# Session Manager - Technical Design Document (TDD)

## 1. 개요

### 1.1 문서 목적
본 문서는 Session Manager의 기술적 설계를 상세히 기술합니다.

### 1.2 범위
- 시스템 아키텍처
- 데이터 모델
- API 상세 설계
- 인프라 구성

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
                                    ┌─────────────────┐
                                    │   Load Balancer │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
             ┌──────▼──────┐          ┌──────▼──────┐          ┌──────▼──────┐
             │   SM API    │          │   SM API    │          │   SM API    │
             │ Instance 1  │          │ Instance 2  │          │ Instance N  │
             └──────┬──────┘          └──────┬──────┘          └──────┬──────┘
                    │                        │                        │
                    └────────────────────────┼────────────────────────┘
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    │                                                  │
             ┌──────▼──────┐                                   ┌──────▼──────┐
             │    Redis    │                                   │ PostgreSQL  │
             │   Cluster   │                                   │  Primary    │
             │             │                                   │      │      │
             │ ┌─────────┐ │                                   │      ▼      │
             │ │ Session │ │                                   │  Replica    │
             │ │  Cache  │ │                                   └─────────────┘
             │ ├─────────┤ │
             │ │  Task   │ │
             │ │  Queue  │ │
             │ └─────────┘ │
             └─────────────┘
```

### 2.2 컴포넌트 설명

| 컴포넌트 | 역할 | 기술 |
|----------|------|------|
| SM API | REST API 서버 | FastAPI |
| Redis | 세션 캐시, Task Queue | Redis 7.x |
| PostgreSQL | 영속 저장소 | PostgreSQL 15 |

### 2.3 통신 방식

| 구간 | 프로토콜 | 특성 |
|------|----------|------|
| Client → SM | HTTP/HTTPS | Sync, REST |
| SM → Redis | TCP | Sync, Direct |
| SM → PostgreSQL | TCP | Async, Connection Pool |

---

## 3. 데이터 모델

### 3.1 PostgreSQL Schema

#### sessions 테이블
```sql
CREATE TABLE sessions (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    session_key_scope VARCHAR(10) NOT NULL,  -- global | local
    session_key_value VARCHAR(100) NOT NULL,
    session_state VARCHAR(10) NOT NULL DEFAULT 'start',  -- start | talk | end
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    close_reason VARCHAR(20),  -- user_exit | timeout | transfer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_session_state CHECK (session_state IN ('start', 'talk', 'end')),
    CONSTRAINT chk_close_reason CHECK (close_reason IN ('user_exit', 'timeout', 'transfer'))
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_session_key ON sessions(session_key_scope, session_key_value);
CREATE INDEX idx_sessions_state ON sessions(session_state);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

#### session_status 테이블
```sql
CREATE TABLE session_status (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES sessions(session_id),
    conversation_id VARCHAR(50) NOT NULL,
    turn_id VARCHAR(50),
    conversation_status VARCHAR(10) NOT NULL DEFAULT 'start',
    task_queue_status VARCHAR(10) NOT NULL DEFAULT 'null',  -- null | notnull
    subagent_status VARCHAR(20) NOT NULL DEFAULT 'undefined',  -- undefined | continue | end
    action_owner VARCHAR(50),
    reference_information JSONB,
    cushion_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_conversation_status CHECK (conversation_status IN ('start', 'talk', 'end')),
    CONSTRAINT chk_task_queue_status CHECK (task_queue_status IN ('null', 'notnull')),
    CONSTRAINT chk_subagent_status CHECK (subagent_status IN ('undefined', 'continue', 'end'))
);

CREATE INDEX idx_session_status_session_id ON session_status(session_id);
CREATE INDEX idx_session_status_conversation_id ON session_status(conversation_id);
CREATE UNIQUE INDEX idx_session_status_unique ON session_status(session_id, conversation_id);
```

#### customer_profiles 테이블
```sql
CREATE TABLE customer_profiles (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    context_id VARCHAR(50),
    attribute_key VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    source_system VARCHAR(50) NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE,
    valid_from DATE,
    valid_to DATE,
    batch_period VARCHAR(10),  -- D | W | M
    permission_scope VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT uq_profile_attribute UNIQUE (user_id, attribute_key)
);

CREATE INDEX idx_profiles_user_id ON customer_profiles(user_id);
CREATE INDEX idx_profiles_source ON customer_profiles(source_system);
CREATE INDEX idx_profiles_valid ON customer_profiles(valid_from, valid_to);
```

#### conversation_history 테이블
```sql
CREATE TABLE conversation_history (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL REFERENCES sessions(session_id),
    conversation_id VARCHAR(50) NOT NULL,
    turn_id VARCHAR(50) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- user | assistant | system
    content_masked TEXT,
    outcome VARCHAR(20),  -- normal | fallback | continue
    subagent_status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT chk_role CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE INDEX idx_history_session_id ON conversation_history(session_id);
CREATE INDEX idx_history_conversation_id ON conversation_history(conversation_id);
CREATE INDEX idx_history_created_at ON conversation_history(created_at);
```

### 3.2 Redis Data Structure

#### Session Cache
```
Key: session:{session_id}
Type: Hash
TTL: 3600 (1시간)

Fields:
  - user_id: string
  - channel: string
  - session_state: string (start|talk|end)
  - conversation_id: string
  - conversation_status: string
  - task_queue_status: string (null|notnull)
  - subagent_status: string (undefined|continue|end)
  - action_owner: string
  - last_event: json string
  - expires_at: timestamp
  - updated_at: timestamp
```

#### Task Queue
```
Key: task_queue:{session_id}
Type: Sorted Set (priority 기반 정렬)
Score: priority (낮을수록 높은 우선순위)

Member: JSON string
{
  "task_id": "task_3001",
  "intent": "이체내역_확인",
  "priority": 1,
  "status": "pending|in_progress|completed|failed",
  "task_payload": {...},
  "created_at": "2025-03-16T08:40:06Z"
}
```

#### Task Status
```
Key: task:{task_id}
Type: Hash
TTL: 86400 (24시간)

Fields:
  - session_id: string
  - task_status: string (pending|in_progress|completed|failed)
  - progress: int (0-100)
  - outcome: string (normal|fallback|continue)
  - response_text: string
  - result_payload: json string
  - created_at: timestamp
  - updated_at: timestamp
```

---

## 4. API 상세 설계

### 4.1 세션 생명주기 API

#### POST /api/v1/sessions (CreateInitialSession)

**Request:**
```json
{
  "user_id": "user_1084756",
  "channel": "mobile",
  "session_key": {
    "scope": "global",
    "key": "user_1084756_mobile"
  },
  "request_id": "req_20250316_001"
}
```

**Response (201 Created):**
```json
{
  "session_id": "sess_20250316_0019",
  "conversation_id": "conv_20250316_0019_001",
  "session_state": "start",
  "expires_at": "2025-03-16T09:40:06Z",
  "policy_profile_ref": "policy_default"
}
```

**Flow:**
```
1. session_key로 Redis 캐시 조회
2. 캐시 히트 & 미만료 → 기존 세션 반환
3. 캐시 미스 → PostgreSQL 조회
4. DB 존재 & 미만료 → 캐시 업데이트 후 반환
5. 없거나 만료 → 새 세션 생성 (DB + 캐시)
```

#### GET /api/v1/sessions/resolve (ResolveSession)

**Request:**
```
GET /api/v1/sessions/resolve?session_key_scope=global&session_key_value=user_1084756_mobile&channel=mobile
```

**Response (200 OK):**
```json
{
  "session_id": "sess_20250316_0019",
  "conversation_id": "conv_20250316_0019_001",
  "session_state": "talk",
  "is_first_call": false,
  "task_queue_status": "notnull",
  "subagent_status": "continue",
  "last_event": {
    "event_type": "TASK_COMPLETED",
    "task_id": "task_3001",
    "subagent_id": "agent-account-inquiry",
    "updated_at": "2025-03-16T08:40:08Z"
  },
  "customer_profile_ref": "profile_user_1084756"
}
```

#### PATCH /api/v1/sessions/{session_id} (PatchSessionState)

**Request:**
```json
{
  "conversation_id": "conv_20250316_0019_001",
  "turn_id": "turn_003",
  "session_state": "talk",
  "state_patch": {
    "subagent_status": "continue",
    "action_owner": "master-agent",
    "reference_information": {
      "intent": "이체내역_확인",
      "confidence": 0.95
    },
    "cushion_message": "이체 내역을 확인하고 있습니다."
  }
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "updated_at": "2025-03-16T08:40:08Z"
}
```

**Flow:**
```
1. Redis 캐시 업데이트 (동기)
2. PostgreSQL 스냅샷 저장 (비동기 - background task)
3. 응답 반환
```

#### POST /api/v1/sessions/{session_id}/close (CloseSession)

**Request:**
```json
{
  "conversation_id": "conv_20250316_0019_001",
  "close_reason": "user_exit",
  "final_summary": "이체 내역 조회 완료"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "closed_at": "2025-03-16T08:45:00Z",
  "archived_conversation_id": "arch_conv_20250316_0019_001"
}
```

### 4.2 Task Queue API

#### POST /api/v1/tasks (EnqueueTask)

**Request:**
```json
{
  "session_id": "sess_20250316_0019",
  "conversation_id": "conv_20250316_0019_001",
  "turn_id": "turn_003",
  "intent": "이체내역_확인",
  "priority": 1,
  "session_state": "talk",
  "task_payload": {
    "masked": true,
    "data": {
      "query": "이전 내역을 확인하고 싶어요",
      "skill": "계좌_거래_기록확인"
    }
  }
}
```

**Response (201 Created):**
```json
{
  "status": "accepted",
  "task_id": "task_3001"
}
```

#### GET /api/v1/tasks/{task_id}/status (GetTaskStatus)

**Response (200 OK):**
```json
{
  "task_id": "task_3001",
  "task_status": "in_progress",
  "progress": 50,
  "updated_at": "2025-03-16T08:40:08Z"
}
```

#### GET /api/v1/tasks/{task_id}/result (GetTaskResult)

**Response (200 OK):**
```json
{
  "task_id": "task_3001",
  "task_status": "completed",
  "outcome": "normal",
  "response_text": "최근 이체 내역을 조회했습니다.",
  "result_payload": {
    "transactions": [
      {"date": "2025-03-15", "amount": 50000, "type": "transfer_out"}
    ]
  }
}
```

---

## 5. 서비스 레이어 설계

### 5.1 SessionService

```python
class SessionService:
    def __init__(
        self,
        redis_client: Redis,
        session_repo: SessionRepository,
        status_repo: SessionStatusRepository
    ):
        self.redis = redis_client
        self.session_repo = session_repo
        self.status_repo = status_repo
    
    async def create_session(self, req: SessionCreateRequest) -> SessionResponse:
        """초기 세션 생성"""
        # 1. 기존 세션 확인
        existing = await self._get_cached_session(req.session_key)
        if existing and not self._is_expired(existing):
            return existing
        
        # 2. 새 세션 생성
        session = Session(
            session_id=self._generate_session_id(),
            user_id=req.user_id,
            channel=req.channel,
            session_key_scope=req.session_key.scope,
            session_key_value=req.session_key.key,
            session_state="start",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        # 3. DB 저장
        await self.session_repo.create(session)
        
        # 4. 캐시 저장
        await self._cache_session(session)
        
        return SessionResponse.from_model(session)
    
    async def resolve_session(self, req: SessionResolveRequest) -> SessionResolveResponse:
        """세션 조회/생성"""
        # 1. 캐시 조회
        cached = await self._get_cached_session(req.session_key)
        if cached:
            status = await self._get_cached_status(cached.session_id)
            return self._build_resolve_response(cached, status)
        
        # 2. DB 조회
        session = await self.session_repo.find_by_key(
            req.session_key.scope, 
            req.session_key.key
        )
        
        # 3. 없으면 생성
        if not session:
            session = await self.create_session(...)
        
        # 4. 캐시 업데이트
        await self._cache_session(session)
        
        return self._build_resolve_response(session, status)
    
    async def patch_session_state(
        self, 
        session_id: str, 
        req: SessionPatchRequest
    ) -> SessionPatchResponse:
        """세션 상태 업데이트"""
        # 1. Redis 업데이트 (동기)
        await self._update_cached_status(session_id, req.state_patch)
        
        # 2. DB 스냅샷 저장 (비동기)
        background_tasks.add_task(
            self._save_status_snapshot, 
            session_id, 
            req
        )
        
        return SessionPatchResponse(
            status="success",
            updated_at=datetime.utcnow()
        )
```

### 5.2 TaskService

```python
class TaskService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def enqueue_task(self, req: TaskEnqueueRequest) -> TaskEnqueueResponse:
        """Task Queue에 작업 적재"""
        task_id = self._generate_task_id()
        
        task = {
            "task_id": task_id,
            "session_id": req.session_id,
            "intent": req.intent,
            "priority": req.priority,
            "status": "pending",
            "task_payload": req.task_payload.dict(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Sorted Set에 추가 (priority를 score로)
        await self.redis.zadd(
            f"task_queue:{req.session_id}",
            {json.dumps(task): req.priority}
        )
        
        # Task 상태 Hash 저장
        await self.redis.hset(
            f"task:{task_id}",
            mapping={
                "session_id": req.session_id,
                "task_status": "pending",
                "progress": 0,
                "created_at": datetime.utcnow().isoformat()
            }
        )
        await self.redis.expire(f"task:{task_id}", 86400)  # 24시간 TTL
        
        return TaskEnqueueResponse(status="accepted", task_id=task_id)
    
    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Task 상태 조회"""
        data = await self.redis.hgetall(f"task:{task_id}")
        if not data:
            raise TaskNotFoundError(task_id)
        
        return TaskStatusResponse(
            task_id=task_id,
            task_status=data["task_status"],
            progress=int(data.get("progress", 0)),
            updated_at=data.get("updated_at")
        )
```

---

## 6. 에러 처리

### 6.1 에러 코드 정의

| Code | HTTP Status | Description |
|------|-------------|-------------|
| SM001 | 400 | Invalid request parameters |
| SM002 | 401 | Authentication failed |
| SM003 | 403 | Permission denied |
| SM004 | 404 | Session not found |
| SM005 | 404 | Task not found |
| SM006 | 409 | Session already exists |
| SM007 | 422 | Invalid session state transition |
| SM008 | 500 | Internal server error |
| SM009 | 503 | Redis connection failed |
| SM010 | 503 | Database connection failed |

### 6.2 에러 응답 형식

```json
{
  "error": {
    "code": "SM004",
    "message": "Session not found",
    "detail": "Session with id 'sess_invalid' does not exist",
    "request_id": "req_20250316_001"
  }
}
```

---

## 7. 보안

### 7.1 인증

- API Key 기반 인증 (서비스 간 통신)
- JWT 토큰 (Portal 관리자)

```python
# API Key 검증
async def verify_api_key(api_key: str = Header(..., alias="X-API-Key")):
    if api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key
```

### 7.2 데이터 암호화

- 전송 중: TLS 1.3
- 저장 시: PostgreSQL Transparent Data Encryption (TDE)
- 민감 필드: AES-256 암호화

---

## 8. 모니터링

### 8.1 메트릭

| Metric | Type | Description |
|--------|------|-------------|
| `sm_request_total` | Counter | 총 요청 수 |
| `sm_request_duration_seconds` | Histogram | 요청 처리 시간 |
| `sm_active_sessions` | Gauge | 활성 세션 수 |
| `sm_redis_cache_hit_total` | Counter | 캐시 히트 수 |
| `sm_redis_cache_miss_total` | Counter | 캐시 미스 수 |
| `sm_task_queue_size` | Gauge | Task Queue 크기 |

### 8.2 로깅

```python
# 구조화된 로그 형식
{
  "timestamp": "2025-03-16T08:40:06Z",
  "level": "INFO",
  "service": "session-manager",
  "request_id": "req_20250316_001",
  "session_id": "sess_20250316_0019",
  "action": "create_session",
  "duration_ms": 45,
  "status": "success"
}
```

---

## 9. 배포

### 9.1 컨테이너 설정

- Base Image: `python:3.11-slim`
- Health Check: `/health`
- Graceful Shutdown: 30초

### 9.2 리소스

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 250m | 1000m |
| Memory | 256Mi | 1Gi |

### 9.3 Auto Scaling

- Min Replicas: 2
- Max Replicas: 10
- Target CPU: 70%

---

## 10. 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2025-03-16 | - | 초기 작성 |
