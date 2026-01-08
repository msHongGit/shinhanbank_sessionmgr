# Session Manager Sprint 3 설계 문서 (최종)

> **작성일**: 2026년 1월 7일  
> **버전**: v4.0  
> **상태**: 설계 완료, 구현 진행 중

---

## 📋 Sprint 3 핵심 원칙

### ✅ Session Manager가 관리하는 것
1. **세션 상태 정보** (`sessions` 테이블)
2. **에이전트 세션 매핑** (`agent_sessions` 테이블)
3. **컨텍스트 메타데이터** (`contexts` 테이블)
4. **대화 턴 메타데이터** (`conversation_turns` 테이블 - **텍스트 제외**)

### ❌ Session Manager가 관리하지 않는 것
1. **실제 대화 텍스트/내용** (MA가 관리)
2. **대화 요약** (제외)
3. **Long-term 메모리** (제외)

### 🎯 필수 필드
- `global_session_key` ✅ 필수
- `agent_session_key` ✅ 필수 (기존 local_session_key)
- `turn_id` ✅ 필수

---

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (Sync)                                           │
│    - /sessions : 세션 CRUD                                  │
│    - /agent-sessions : 에이전트 세션 매핑                    │
│    - /contexts : 컨텍스트 메타데이터 관리                    │
│    - 인증: require_api_key([...])                           │
├─────────────────────────────────────────────────────────────┤
│  Service Layer (Sync)                                       │
│    - SessionService: Policy 검증 + 상태 관리                │
│    - ContextService: 컨텍스트 메타데이터 관리                │
│    - BackgroundTasks: Redis 비동기 업데이트                 │
├─────────────────────────────────────────────────────────────┤
│  Core Layer                                                 │
│    - SessionPolicy: 상태 전이 규칙 검증                      │
│    - Auth: require_api_key() 통합 인증                      │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer (Hybrid)                                  │
│    - Redis: 캐시 (동기)                                     │
│    - MariaDB: 영구 저장 (동기)                              │
│    - HybridRepository: Read(Redis) + Write(Both)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ MariaDB 스키마

### 1. sessions 테이블 (세션 상태)
```sql
CREATE TABLE sessions (
    global_session_key VARCHAR(100) PRIMARY KEY,
    conversation_id VARCHAR(100),
    context_id VARCHAR(100),
    user_id VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    
    -- 상태
    session_state VARCHAR(50) NOT NULL,
    subagent_status VARCHAR(50),
    
    -- 턴 추적
    current_turn_id VARCHAR(100),           -- 현재 턴 ID (필수)
    
    -- 에이전트 정보
    current_agent JSON,
    agent_history JSON DEFAULT ('[]'),
    
    -- 메타데이터
    metadata JSON DEFAULT ('{}'),
    state_patch JSON DEFAULT ('{}'),
    
    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_session_state (session_state),
    INDEX idx_turn_id (current_turn_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 2. agent_sessions 테이블 (에이전트 세션 매핑)
```sql
CREATE TABLE agent_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    global_session_key VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    agent_session_key VARCHAR(100) NOT NULL,  -- 기존 local_session_key
    agent_type VARCHAR(50) NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_global_agent (global_session_key, agent_id),
    INDEX idx_global (global_session_key),
    INDEX idx_agent_session (agent_session_key),
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 3. contexts 테이블 (컨텍스트 메타데이터)
```sql
CREATE TABLE contexts (
    context_id VARCHAR(100) PRIMARY KEY,
    global_session_key VARCHAR(100) NOT NULL,
    
    -- 현재 대화 상태
    current_intent VARCHAR(100),
    current_slots JSON DEFAULT ('{}'),      -- {amount: "100만원", currency: "USD"}
    entities JSON DEFAULT ('[]'),           -- 추출된 엔티티 목록
    
    -- 카운터
    turn_count INTEGER DEFAULT 0,
    
    -- 메타데이터
    metadata JSON DEFAULT ('{}'),
    
    -- 타임스탬프
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    
    INDEX idx_session (global_session_key),
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 4. conversation_turns 테이블 (대화 턴 메타데이터 - 텍스트 제외)
```sql
CREATE TABLE conversation_turns (
    turn_id VARCHAR(100) PRIMARY KEY,
    context_id VARCHAR(100) NOT NULL,
    global_session_key VARCHAR(100) NOT NULL,
    
    -- 턴 정보
    turn_number INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,              -- user, assistant, system
    
    -- 에이전트 정보
    agent_id VARCHAR(100),
    agent_type VARCHAR(50),
    
    -- 메타데이터 (실제 텍스트 제외, 나머지 모든 정보)
    metadata JSON DEFAULT ('{}'),           -- {
                                            --   intent: "exchange_currency",
                                            --   confidence: 0.95,
                                            --   slots: {amount: "100만원"},
                                            --   entities: ["amount", "currency"],
                                            --   response_type: "ask_back"
                                            -- }
    
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_context (context_id),
    INDEX idx_session (global_session_key),
    INDEX idx_turn_number (context_id, turn_number),
    FOREIGN KEY (context_id) REFERENCES contexts(context_id) ON DELETE CASCADE,
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**conversation_turns.metadata 예시:**
```json
{
  "intent": "exchange_currency",
  "confidence": 0.95,
  "slots": {
    "amount": "100만원",
    "currency": "USD"
  },
  "entities": ["amount", "currency"],
  "response_type": "ask_back",
  "matched_skill_id": "sa_exchange"
}
```

---

## 📡 API 명세

### 1. POST /api/v1/sessions
**세션 생성**

```http
POST /api/v1/sessions
X-API-Key: {AGW_API_KEY}
Content-Type: application/json

{
  "user_id": "user-001",
  "channel": "mobile",
  "request_id": "req-001"
}
```

**Response:**
```json
{
  "global_session_key": "gsess_20260107_abc123",
  "conversation_id": "conv_20260107_xyz",
  "context_id": "ctx_20260107_xyz",
  "session_state": "start",
  "expires_at": "2026-01-07T11:30:00Z"
}
```

---

### 2. PATCH /api/v1/sessions/{global_session_key}/state
**세션 상태 업데이트 (turn_id 필수)**

```http
PATCH /api/v1/sessions/gsess_20260107_abc123/state
X-API-Key: {MA_API_KEY}
Content-Type: application/json

{
  "global_session_key": "gsess_20260107_abc123",
  "turn_id": "turn_20260107_001",           // 필수
  "conversation_id": "conv_20260107_xyz",
  "session_state": "talk",
  "state_patch": {
    "subagent_status": "continue",
    "intent": "exchange_currency",
    "pending_slots": ["amount"]
  }
}
```

**Response:**
```json
{
  "global_session_key": "gsess_20260107_abc123",
  "session_state": "talk",
  "current_turn_id": "turn_20260107_001",
  "state_patch": {
    "subagent_status": "continue",
    "intent": "exchange_currency",
    "pending_slots": ["amount"]
  },
  "updated_at": "2026-01-07T10:35:00Z"
}
```

---

### 3. POST /api/v1/agent-sessions
**에이전트 세션 매핑 등록**

```http
POST /api/v1/agent-sessions
X-API-Key: {MA_API_KEY}
Content-Type: application/json

{
  "global_session_key": "gsess_20260107_abc123",
  "agent_id": "sa_exchange_001",
  "agent_session_key": "asess_exchange_xyz"
}
```

**Response:**
```json
{
  "global_session_key": "gsess_20260107_abc123",
  "agent_id": "sa_exchange_001",
  "agent_session_key": "asess_exchange_xyz",
  "registered_at": "2026-01-07T10:30:00Z"
}
```

---

### 4. GET /api/v1/agent-sessions
**에이전트 세션 조회**

```http
GET /api/v1/agent-sessions?global_session_key=gsess_xxx&agent_id=sa_exchange_001
X-API-Key: {MA_API_KEY}
```

**Response:**
```json
{
  "global_session_key": "gsess_20260107_abc123",
  "agent_id": "sa_exchange_001",
  "agent_session_key": "asess_exchange_xyz"
}
```

---

### 5. POST /api/v1/contexts/{context_id}/turns
**대화 턴 메타데이터 저장 (텍스트 제외)**

```http
POST /api/v1/contexts/ctx_20260107_xyz/turns
X-API-Key: {MA_API_KEY}
Content-Type: application/json

{
  "turn_id": "turn_20260107_001",
  "global_session_key": "gsess_20260107_abc123",
  "turn_number": 1,
  "role": "user",
  "agent_id": "ma_001",
  "agent_type": "master",
  "metadata": {
    "intent": "exchange_currency",
    "confidence": 0.95,
    "entities": ["amount", "currency"]
  }
}
```

**Response:**
```json
{
  "turn_id": "turn_20260107_001",
  "context_id": "ctx_20260107_xyz",
  "turn_number": 1,
  "timestamp": "2026-01-07T10:30:00Z"
}
```

---

### 6. GET /api/v1/contexts/{context_id}/turns
**대화 턴 메타데이터 조회**

```http
GET /api/v1/contexts/ctx_xxx/turns?limit=10
X-API-Key: {MA_API_KEY}
```

**Response:**
```json
{
  "context_id": "ctx_20260107_xyz",
  "turns": [
    {
      "turn_id": "turn_20260107_001",
      "turn_number": 1,
      "role": "user",
      "agent_id": "ma_001",
      "metadata": {
        "intent": "exchange_currency",
        "confidence": 0.95
      },
      "timestamp": "2026-01-07T10:30:00Z"
    },
    {
      "turn_id": "turn_20260107_002",
      "turn_number": 2,
      "role": "assistant",
      "agent_id": "sa_exchange",
      "metadata": {
        "response_type": "ask_back",
        "pending_slots": ["amount"]
      },
      "timestamp": "2026-01-07T10:30:05Z"
    }
  ],
  "total_count": 2
}
```

---

### 7. PATCH /api/v1/contexts/{context_id}
**컨텍스트 메타데이터 업데이트**

```http
PATCH /api/v1/contexts/ctx_xxx
X-API-Key: {MA_API_KEY}
Content-Type: application/json

{
  "current_intent": "exchange_currency",
  "current_slots": {
    "amount": "100만원",
    "currency": "USD"
  },
  "entities": ["amount", "currency"]
}
```

---

## 🔄 데이터 저장 흐름

### 예시: "100만원 환전해줘" 대화

```
1. 세션 생성 (AGW)
   POST /api/v1/sessions
   → global_session_key, context_id 발급

2. 턴 1: 사용자 입력 (MA)
   POST /api/v1/contexts/{context_id}/turns
   {
     "turn_id": "turn_001",
     "role": "user",
     "metadata": {
       "input_length": 10  // 텍스트 저장 안 함
     }
   }

3. 의도 분류 완료 (MA)
   PATCH /api/v1/contexts/{context_id}
   {
     "current_intent": "exchange_currency",
     "entities": ["amount"]
   }

4. 세션 상태 업데이트 (MA)
   PATCH /api/v1/sessions/{key}/state
   {
     "turn_id": "turn_001",
     "session_state": "talk",
     "state_patch": {
       "intent": "exchange_currency"
     }
   }

5. SA 실행 시작 (MA)
   PATCH /api/v1/sessions/{key}/state
   {
     "turn_id": "turn_002",
     "session_state": "task"
     }

6. 턴 2: SA 응답 (MA)
   POST /api/v1/contexts/{context_id}/turns
   {
     "turn_id": "turn_002",
     "role": "assistant",
     "agent_id": "sa_exchange",
     "metadata": {
       "response_type": "ask_back",
       "pending_slots": ["currency"]
     }
   }
```

---

## 💾 Redis 데이터 구조

### 세션 캐시
```
Key: session:{global_session_key}
Type: Hash
TTL: 3600 (1시간)
Fields:
  - conversation_id
  - context_id
  - user_id
  - session_state
  - current_turn_id
  - subagent_status
  - current_agent (JSON)
  - state_patch (JSON)
  - created_at
  - updated_at
```

### 컨텍스트 캐시
```
Key: context:{context_id}
Type: Hash
TTL: 3600
Fields:
  - global_session_key
  - current_intent
  - current_slots (JSON)
  - entities (JSON)
  - turn_count
```

### 에이전트 세션 매핑
```
Key: agent_session:{global_session_key}:{agent_id}
Type: String
TTL: 3600
Value: agent_session_key
```

---

## 🔧 구현 체크리스트

### Phase 1: 스키마 구현
- [ ] Pydantic 스키마
  - [ ] `schemas/sessions.py`: `turn_id` 필수화
  - [ ] `schemas/agent_sessions.py` (기존 local_sessions 이름 변경)
  - [ ] `schemas/contexts.py`: 컨텍스트 메타데이터
  - [ ] `schemas/turns.py`: 턴 메타데이터 (content 제외)

### Phase 2: MariaDB 연결
- [ ] `app/db/mariadb.py`: SQLAlchemy 동기 엔진
- [ ] 테이블 생성 스크립트 (`scripts/init_db.sql`)
- [ ] Alembic 마이그레이션 설정

### Phase 3: Repository 구현
- [ ] `repositories/mariadb/session_repository.py`
- [ ] `repositories/mariadb/agent_session_repository.py`
- [ ] `repositories/mariadb/context_repository.py`
- [ ] `repositories/mariadb/turn_repository.py`
- [ ] `repositories/hybrid/session_repository.py`

### Phase 4: Service 구현
- [ ] `services/session_service.py`: `turn_id` 필수 검증
- [ ] `services/context_service.py`: 컨텍스트/턴 관리
- [ ] BackgroundTasks 통합

### Phase 5: API 구현
- [ ] `api/v1/sessions.py`: `turn_id` 필수화
- [ ] `api/v1/agent_sessions.py` (이름 변경)
- [ ] `api/v1/contexts.py`: 컨텍스트/턴 API
- [ ] Router 업데이트

### Phase 6: 테스트
- [ ] `turn_id` 필수 검증 테스트
- [ ] 턴 메타데이터 저장/조회 테스트
- [ ] BackgroundTasks 테스트
- [ ] 시나리오 테스트

---

## 📊 성능 목표

| 지표 | 목표 |
|------|------|
| 세션 생성 응답 시간 | < 10ms |
| 세션 조회 응답 시간 | < 5ms (Redis 캐시) |
| 세션 업데이트 응답 시간 | < 10ms |
| 컨텍스트 조회 응답 시간 | < 20ms |
| Redis 캐시 히트율 | > 95% |

---

## 🚀 다음 단계

1. MariaDB 연결 구현
2. Repository 계층 완성
3. Context/Turn API 구현
4. 테스트 작성 및 실행

---

**작성자**: Session Manager Team  
**최종 수정**: 2026년 1월 7일
