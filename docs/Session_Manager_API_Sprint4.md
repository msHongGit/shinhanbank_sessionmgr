# Session Manager API 명세 (Sprint 4 기준)

> **Sprint 4 구현 기준** – MariaDB 영구 저장소 통합, 필드명 통일, Context DB 구축  
> **Session Manager 역할**: 세션/컨텍스트/프로파일 메타데이터 저장 및 조회 (Redis 동기 + MariaDB 비동기)

---

## 0. Sprint 3 문서와 무엇이 달라졌나?

이 문서는 기존 [docs/Session_Manager_API_Sprint3.md](Session_Manager_API_Sprint3.md) 기준에서 **Sprint 4 실제 코드**에 맞게 정리한 버전입니다.

### 주요 변경사항

#### 1. MariaDB 영구 저장소 통합
- **Sprint 3**: Redis만 사용 (캐시)
- **Sprint 4**: Redis (동기) + MariaDB (비동기) 하이브리드 저장소
  - Redis: 즉시 응답을 위한 동기 저장 (캐시)
  - MariaDB: 영구 저장을 위한 비동기 저장 (BackgroundTasks)
  - 세션 생성/업데이트/종료 시 자동으로 MariaDB에 저장

#### 2. 필드명 통일
- **`session_id` 제거**: Redis에서 중복 필드 제거 (`global_session_key`만 사용)
- **`local_session_key` → `agent_session_key`**: 모든 코드에서 통일
- **`current_subagent_id` → `action_owner`**: MariaDB 필드명을 Redis에 맞춤
- **`last_updated_at` → `updated_at`**: MariaDB 필드명을 Redis에 맞춤

#### 3. Context DB 구축
- MariaDB에 Context/Turn 메타데이터 저장
- SOL API 연동 결과도 MariaDB에 비동기 저장

#### 4. Agent 세션 매핑 영구 저장
- Redis `session_map` 데이터를 MariaDB `agent_sessions` 테이블에 저장
- 세션 업데이트 시 Agent 매핑도 함께 저장

---

## 1. 공통 정보

### 1.1 베이스 URL (예시)

| 환경           | Base URL                               | 비고                           |
|----------------|-----------------------------------------|--------------------------------|
| 로컬 개발      | `http://localhost:5000`                | `uv run uvicorn app.main:app` |
| Docker 로컬    | `http://localhost:5000`                | `docker run -p 5000:5000`     |
| Azure Dev      | `http://sol-session-manager.crewai-axd.com`  |                 |

- API Prefix: `/api/v1`
- Swagger UI: `{BASE_URL}/api/v1/docs`
- OpenAPI JSON: `{BASE_URL}/api/v1/openapi.json`
- Health: `/` (GET)

### 1.2 인증 (API Key 설계 – 현재 Dev에서는 비활성화 가능)

- 헤더: `X-API-Key: {CALLER_API_KEY}`
- 호출자별 키 (환경변수 예시 이름만 사용):

| Caller   | 환경변수         |
|----------|------------------|
| AGW      | `AGW_API_KEY`    |
| MA       | `MA_API_KEY`     |
| Portal   | `PORTAL_API_KEY` |
| VDB/배치 | `VDB_API_KEY`    |
| External | `EXTERNAL_API_KEY` |

> 현재 Sprint 4 개발 브랜치에서는 `sessions`, `contexts` 라우터에 API Key 의존성이 제거되어 있어, 로컬/Dev에서는 인증 없이 호출 가능합니다.  
> 운영 환경에서는 `ENABLE_API_KEY_AUTH=true` + `require_api_key()` 복구를 전제로 설계합니다.

---

## 2. 세션 API (Unified Sessions)

라우터: `app/api/v1/sessions.py`  
Prefix: `/api/v1/sessions`

### 2.1 세션 생성

**Endpoint**

```http
POST /api/v1/sessions
```

**언제 사용하나?**

- AGW/Client가 **처음 상담 시작** 시
- 이미 같은 세션에 살아 있다면 **기존 세션 재사용** (`is_new=false`)
- 이때 Session Manager가:
  - `global_session_key` 자동 발급 (응답에 포함)
  - `context_id` 자동 발급 (내부적으로 생성, 응답에는 미포함)
  - 프로파일 저장소에서 개인화 프로파일 조회 후 세션에 저장 (조회 시 포함)
  - **Redis에 즉시 저장** (동기)
  - **MariaDB에 비동기 저장** (BackgroundTasks)

**Request Body – `SessionCreateRequest`**

```json
{
  "userId": "user_001",
  "channel": {
    "eventType": "ICON_ENTRY",
    "eventChannel": "web"
  }
}
```

| 필드      | 타입   | 필수 | 설명                                                                 |
|-----------|--------|------|----------------------------------------------------------------------|
| userId    | string | ✅   | 사용자 ID                                                            |
| channel   | object | ❌   | 이벤트/채널 정보 딕셔너리 (없으면 기본 채널 `utterance` 로 처리)    |

`channel` 필드 구조:

```json
"channel": {
  "eventType": "ICON_ENTRY",   // 기존 startType 개념
  "eventChannel": "web"        // 기존 channel (web, kiosk 등)
}
```

**Response Body – `SessionCreateResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234"
}
```

| 필드               | 타입   | 설명                                                             |
|--------------------|--------|------------------------------------------------------------------|
| global_session_key | string | 세션 전체를 대표하는 **글로벌 세션 ID** (이후 모든 호출에 사용) |

**저장 흐름**

1. Redis에 즉시 저장 (동기) → API 응답 반환
2. BackgroundTasks로 MariaDB에 비동기 저장 (응답 후 실행)

---

### 2.2 세션 조회

**Endpoint**

```http
GET /api/v1/sessions/{global_session_key}
```

**Query Parameters**

```http
GET /api/v1/sessions/gsess_20260108_abcd1234?agent_type=task&agent_id=transfer_agent
```

| 파라미터   | 타입             | 필수 | 설명                                                              |
|------------|------------------|------|-------------------------------------------------------------------|
| agent_type | `AgentType` enum | ❌   | Agent 유형 (`task`/`knowledge` 등, 업무 Agent면 보통 `task`)     |
| agent_id   | string           | ❌   | Agent ID (예: `transfer_agent`, `dbs_caller`)                     |

**Response Body – `SessionResolveResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "user_id": "user_001",
  "channel": {
    "eventType": "ICON_ENTRY",
    "eventChannel": "web"
  },
  "agent_session_key": "asess_transfer_001",
  "session_state": "talk",
  "is_first_call": false,
  "task_queue_status": "null",
  "subagent_status": "continue",
  "last_event": {
    "event_type": "AGENT_RESPONSE",
    "agent_id": "transfer_agent",
    "agent_type": "task",
    "response_type": "text",
    "updated_at": "2026-01-14T10:30:00Z"
  },
  "customer_profile": {
    "user_id": "user_001",
    "attributes": [],
    "segment": "VIP",
    "preferences": {
      "marketing_opt_in": true
    }
  },
  "active_task": {
    "task_id": "task-001",
    "intent": "계좌조회",
    "skill_tag": "balance_inquiry"
  },
  "conversation_history": [
    {"role": "user", "content": "계좌 잔액 조회해주세요"},
    {"role": "assistant", "content": "계좌번호를 알려주세요."}
  ],
  "current_intent": "계좌조회",
  "current_task_id": "task-001",
  "task_queue_status_detail": [
    {
      "task_id": "task-001",
      "intent": "계좌조회",
      "status": "Running",
      "skill_tag": "balance_inquiry"
    }
  ],
  "turn_count": 1,
  "turn_ids": ["turn_001", "turn_002"],
  "reference_information": {
    "conversation_history": [...],
    "current_intent": "계좌조회",
    "turn_count": 1,
    "active_task": {...},
    "task_queue_status": [...]
  }
}
```

| 필드               | 타입   | 설명                                                                 |
|--------------------|--------|----------------------------------------------------------------------|
| global_session_key        | string         | 조회된 세션의 글로벌 세션 키                                               |
| user_id                   | string         | 세션 사용자 ID (세션 생성 시 전달한 userId)                               |
| channel                   | object         | 세션 채널/이벤트 정보 (`eventType`, `eventChannel`)                         |
| agent_session_key         | string         | 업무 Agent 로컬 세션 키 (요청 시 `agent_type`+`agent_id` 가 있을 때만 세팅) |
| session_state             | string         | 세션 상태 (`start` / `talk` / `end`)                                       |
| is_first_call             | bool           | 세션이 `start` 상태인지 여부                                               |
| task_queue_status         | string         | 백엔드 Task Queue 상태 (`null` / `notnull`)                                 |
| subagent_status           | string         | SubAgent 상태 (`undefined` / `continue` / `end`)                            |
| last_event                | object         | 마지막 이벤트 정보 (없으면 `null`)                                          |
| customer_profile          | object         | 고객 개인화 프로파일 스냅샷 (없으면 `null`)                                 |
| active_task               | object\|null | DirectRouting용 활성 태스크 정보 (`reference_information.active_task`)      |
| conversation_history      | array\|null  | 최근 대화 이력 (`reference_information.conversation_history`)               |
| current_intent            | string\|null | 현재 활성 의도 (`reference_information.current_intent`)                     |
| current_task_id           | string\|null | 현재 태스크 ID (`reference_information.current_task_id`)                    |
| task_queue_status_detail  | array\|null  | 태스크 큐 상세 상태 (`reference_information.task_queue_status`)            |
| turn_count                | integer\|null | 대화 턴 수 (`reference_information.turn_count`)                             |
| turn_ids                  | array          | 누적 턴 ID 목록                                                              |
| reference_information     | object         | 전체 reference_information 원본 (raw)                                       |

**조회 흐름**

1. Redis에서 세션 조회 (캐시)
2. `reference_information` 파싱하여 상위 필드로 추출
3. Agent 매핑 조회 (Redis `session_map`)

---

### 2.3 세션 상태 업데이트

**Endpoint**

```http
PATCH /api/v1/sessions/{global_session_key}/state
```

**언제 사용하나?**

- MA가 세션 상태를 업데이트할 때
- 멀티턴 컨텍스트(`reference_information`)를 저장할 때
- Agent 세션 매핑을 등록할 때

**Request Body – `SessionPatchRequest`**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "turn_id": "turn_002",
  "session_state": "talk",
  "state_patch": {
    "subagent_status": "continue",
    "action_owner": "transfer_agent",
    "current_intent": "계좌이체",
    "turn_count": 2,
    "reference_information": {
      "conversation_history": [
        {"role": "user", "content": "계좌 이체하고 싶어요"},
        {"role": "assistant", "content": "이체할 계좌번호를 알려주세요"}
      ],
      "current_intent": "계좌이체",
      "turn_count": 2,
      "active_task": {
        "task_id": "task-002",
        "intent": "계좌이체",
        "skill_tag": "transfer"
      }
    },
    "agent_session_key": "asess_transfer_002",
    "last_agent_id": "transfer_agent",
    "last_agent_type": "task",
    "last_response_type": "text",
    "cushion_message": "잠시만 기다려주세요",
    "session_attributes": {
      "source": "web"
    }
  }
}
```

| 필드               | 타입   | 필수 | 설명                                                                 |
|--------------------|--------|------|----------------------------------------------------------------------|
| global_session_key | string | ✅   | 세션 키                                                              |
| turn_id            | string | ❌   | 턴 ID (전달 시 세션의 `turn_ids` 리스트에 누적)                      |
| session_state      | string | ❌   | 세션 상태 (`start` / `talk` / `end`)                                  |
| state_patch        | object | ❌   | 상태 패치 객체                                                        |

`state_patch` 필드 구조:

| 필드                  | 타입   | 필수 | 설명                                                                 |
|-----------------------|--------|------|----------------------------------------------------------------------|
| subagent_status       | string | ❌   | SubAgent 상태 (`undefined` / `continue` / `end`)                      |
| action_owner           | string | ❌   | 현재 액션 담당자 (Agent ID)                                           |
| current_intent         | string | ❌   | 현재 의도 (최상위 또는 `reference_information` 내부)                 |
| turn_count             | integer| ❌   | 턴 수 (최상위 또는 `reference_information` 내부)                      |
| reference_information  | object | ❌   | 멀티턴 컨텍스트 (dict, 내부 필드 타입 검증)                           |
| agent_session_key      | string | ❌   | Agent 로컬 세션 키 (매핑 등록용)                                     |
| last_agent_id          | string | ❌   | 마지막 응답 Agent ID                                                  |
| last_agent_type        | string | ❌   | 마지막 응답 Agent 타입 (`task` / `knowledge`)                       |
| last_response_type     | string | ❌   | 마지막 응답 타입 (`text` / `card` 등)                                 |
| cushion_message        | string | ❌   | 쿠션 메시지                                                           |
| session_attributes     | object | ❌   | 세션 속성 (dict)                                                      |

**`reference_information` 구조 및 검증**

- 최상위는 반드시 `dict` 타입이어야 함
- 내부 필드:
  - `conversation_history`: `list` 타입 (각 원소는 최소 `{"role": str, "content": str}` 형태)
  - `turn_count`: `int` 타입
  - 기타 필드는 자유롭게 추가 가능

**Response Body – `SessionPatchResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "session_state": "talk",
  "updated_at": "2026-01-14T10:30:00Z"
}
```

**저장 흐름**

1. Redis에 즉시 업데이트 (동기) → API 응답 반환
2. BackgroundTasks로 MariaDB에 비동기 저장:
   - 세션 정보 업데이트
   - Agent 세션 매핑 저장 (`agent_session_key` + `last_agent_id`가 있을 때)

---

### 2.4 세션 종료

**Endpoint**

```http
DELETE /api/v1/sessions/{global_session_key}
```

**Request Body – `SessionCloseRequest`**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "close_reason": "user_exit",
  "final_summary": "이체 완료"
}
```

| 필드               | 타입   | 필수 | 설명                    |
|--------------------|--------|------|-------------------------|
| global_session_key | string | ✅   | 세션 키                  |
| close_reason       | string | ❌   | 종료 사유                |
| final_summary      | string | ❌   | 최종 요약 (1000자 이내)  |

**Response Body**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "session_state": "end",
  "ended_at": "2026-01-14T10:35:00Z"
}
```

**저장 흐름**

1. Redis에 세션 상태를 `end`로 업데이트 (동기)
2. BackgroundTasks로 MariaDB에 비동기 저장:
   - 세션 종료 정보 (`ended_at`, `close_reason`, `final_summary`) 저장

---

### 2.5 세션 생존 확인 (Ping)

**Endpoint**

```http
GET /api/v1/sessions/{global_session_key}/ping
```

**Response Body**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "is_alive": true,
  "expires_at": "2026-01-14T10:45:00Z"
}
```

- 세션 TTL 연장 (기본 600초)
- Redis `expires_at` 갱신

---

## 3. Contexts API

라우터: `app/api/v1/contexts.py`  
Prefix: `/api/v1/contexts`

### 3.1 SOL API 결과 저장

**Endpoint**

```http
POST /api/v1/contexts/turn-results
```

**언제 사용하나?**

- SOL API (`/api/v1/sol/transaction`, `/api/v1/sol/transaction/result`) 호출 결과를 저장할 때
- 실시간 API 연동 로그를 턴 메타데이터로 저장

**Request Body – `SolApiResultRequest`**

```json
{
  "sessionId": "gsess_20260108_abcd1234",
  "turnId": "turn_002",
  "agent": "balance_agent",
  "result": "SUCCESS",
  "transactionResult": [
    {
      "trxCd": "BAL001",
      "requestData": {"accountNo": "1234567890"},
      "responseData": {"balance": 500000}
    }
  ]
}
```

| 필드              | 타입   | 필수 | 설명                                    |
|-------------------|--------|------|-----------------------------------------|
| sessionId         | string | ✅   | 세션 ID (`global_session_key`)          |
| turnId            | string | ✅   | 턴 ID                                   |
| agent             | string | ❌   | Agent ID                                |
| result             | string | ❌   | 결과 상태 (`SUCCESS` / `FAILURE` 등)     |
| transactionResult | array  | ❌   | SOL API 트랜잭션 결과 배열               |

**Response Body – `TurnResponse`**

```json
{
  "turn_id": "turn_002",
  "context_id": "ctx_20260108_001",
  "global_session_key": "gsess_20260108_abcd1234",
  "turn_number": null,
  "role": null,
  "agent_id": null,
  "agent_type": null,
  "metadata": {
    "sol_api": {
      "sessionId": "gsess_20260108_abcd1234",
      "turnId": "turn_002",
      "agent": "balance_agent",
      "response": {
        "result": "SUCCESS",
        "transactionResult": [
          {
            "trxCd": "BAL001",
            "responseData": {"balance": 500000}
          }
        ]
      }
    }
  },
  "timestamp": "2026-01-14T10:30:00Z"
}
```

| 필드              | 타입   | 설명                                    |
|-------------------|--------|-----------------------------------------|
| turn_id           | string | 턴 ID (요청의 turnId)                  |
| context_id        | string | 컨텍스트 ID                             |
| global_session_key| string | 글로벌 세션 키                           |
| metadata          | object | 메타데이터 (sol_api 블록 포함)           |
| timestamp         | string | 저장 시각 (ISO 8601 형식)               |

**저장 흐름**

1. Redis에 턴 메타데이터 저장 (동기)
2. BackgroundTasks로 MariaDB에 비동기 저장:
   - `conversation_turns` 테이블에 턴 메타데이터 저장

---

### 3.2 세션 전체 정보 조회

**Endpoint**

```http
GET /api/v1/contexts/sessions/{global_session_key}/full
```

**언제 사용하나?**

- 세션 메타데이터와 모든 턴 목록을 한 번에 조회할 때
- Portal/관리자 대시보드에서 세션 상세 정보 확인

**Response Body – `SessionFullResponse`**

```json
{
  "session": {
    "global_session_key": "gsess_20260108_abcd1234",
    "user_id": "user_001",
    "channel": "web",
    "session_state": "talk",
    "task_queue_status": "null",
    "subagent_status": "continue",
    "action_owner": "transfer_agent",
    "reference_information": {...},
    "turn_ids": ["turn_001", "turn_002"],
    "start_type": "ICON_ENTRY",
    "created_at": "2026-01-14T10:00:00Z",
    "updated_at": "2026-01-14T10:30:00Z"
  },
  "turns": [
    {
      "turn_id": "turn_001",
      "context_id": "ctx_20260108_001",
      "turn_number": 1,
      "role": "user",
      "agent_id": null,
      "agent_type": null,
      "turn_metadata": {
        "intent": "계좌조회",
        "confidence": 0.95
      },
      "timestamp": "2026-01-14T10:05:00Z"
    },
    {
      "turn_id": "turn_002",
      "context_id": "ctx_20260108_001",
      "turn_number": 2,
      "role": "assistant",
      "agent_id": "balance_agent",
      "agent_type": "task",
      "turn_metadata": {
        "transactionResult": [
          {
            "trxCd": "BAL001",
            "responseData": {"balance": 500000}
          }
        ]
      },
      "timestamp": "2026-01-14T10:10:00Z"
    }
  ],
  "total_turns": 2
}
```

**조회 흐름**

1. Redis에서 세션 조회
2. Redis에서 턴 목록 조회 (`context_turns:{context_id}`)
3. 통합하여 응답 반환

---

## 4. 저장소 구조

### 4.1 Redis (동기 저장)

**세션 정보**

- 키: `session:{global_session_key}`
- 타입: Hash
- 필드:
  - `global_session_key`: 세션 키
  - `user_id`: 사용자 ID
  - `channel`: 채널 정보
  - `conversation_id`: 대화 ID
  - `context_id`: 컨텍스트 ID
  - `session_state`: 세션 상태
  - `task_queue_status`: Task Queue 상태
  - `subagent_status`: SubAgent 상태
  - `action_owner`: 현재 액션 담당자
  - `reference_information`: 멀티턴 컨텍스트 (JSON 문자열)
  - `turn_ids`: 턴 ID 목록 (JSON 문자열)
  - `profile`: 프로파일 (JSON 문자열)
  - `customer_profile`: 고객 프로파일 스냅샷 (JSON 문자열)
  - `start_type`: 세션 진입 유형
  - `cushion_message`: 쿠션 메시지
  - `session_attributes`: 세션 속성 (JSON 문자열)
  - `last_event`: 마지막 이벤트 (JSON 문자열)
  - `close_reason`: 종료 사유
  - `final_summary`: 최종 요약
  - `ended_at`: 종료 시각
  - `expires_at`: 만료 시각
  - `created_at`: 생성 시각
  - `updated_at`: 업데이트 시각
- TTL: `SESSION_CACHE_TTL` (기본 600초)

**Agent 세션 매핑**

- 키: `session_map:{global_session_key}:{agent_id}`
- 타입: Hash
- 필드:
  - `global_session_key`: 글로벌 세션 키
  - `agent_session_key`: Agent 로컬 세션 키
  - `agent_id`: Agent ID
  - `agent_type`: Agent 타입 (`task` / `knowledge`)
- TTL: `SESSION_MAP_TTL` (기본 600초)

**컨텍스트 정보**

- 키: `context:{context_id}`
- 타입: Hash
- 필드: 컨텍스트 메타데이터

**턴 목록**

- 키: `context_turns:{context_id}`
- 타입: List
- 값: 턴 메타데이터 (JSON 문자열)

---

### 4.2 MariaDB (비동기 저장)

**스키마 파일**: `scripts/init_db.sql`

#### sessions 테이블

```sql
CREATE TABLE sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_session_key VARCHAR(255) NOT NULL UNIQUE,
    conversation_id VARCHAR(255) NOT NULL,
    context_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50),
    user_id VARCHAR(255),
    session_state VARCHAR(20) NOT NULL DEFAULT 'start',
    task_queue_status VARCHAR(20) DEFAULT 'null',
    subagent_status VARCHAR(20) DEFAULT 'undefined',
    action_owner VARCHAR(255),
    reference_information JSON,
    turn_ids JSON,
    start_type VARCHAR(50),
    ended_at DATETIME(6),
    close_reason VARCHAR(100),
    final_summary VARCHAR(1000),
    metadata JSON,
    profile JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    expires_at DATETIME(6),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_conversation_id (conversation_id),
    INDEX idx_user_id (user_id),
    INDEX idx_sessions_state_updated (session_state, updated_at)
);
```

#### agent_sessions 테이블

```sql
CREATE TABLE agent_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    global_session_key VARCHAR(255) NOT NULL,
    agent_session_key VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    expires_at DATETIME(6),
    UNIQUE KEY unique_mapping (global_session_key, agent_id),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_agent_session_key (agent_session_key),
    INDEX idx_agent_id (agent_id),
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
);
```

#### contexts 테이블

```sql
CREATE TABLE contexts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    context_id VARCHAR(255) NOT NULL UNIQUE,
    global_session_key VARCHAR(255) NOT NULL,
    current_intent VARCHAR(255),
    current_slots JSON,
    entities JSON,
    turn_count INT NOT NULL DEFAULT 0,
    metadata JSON,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_context_id (context_id),
    INDEX idx_global_session_key (global_session_key),
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
);
```

#### conversation_turns 테이블

```sql
CREATE TABLE conversation_turns (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    turn_id VARCHAR(255) NOT NULL UNIQUE,
    context_id VARCHAR(255) NOT NULL,
    global_session_key VARCHAR(255) NOT NULL,
    turn_number INT NOT NULL,
    role VARCHAR(20) NOT NULL,
    agent_id VARCHAR(255),
    agent_type VARCHAR(50),
    metadata JSON,
    timestamp DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    INDEX idx_turn_id (turn_id),
    INDEX idx_context_id (context_id),
    INDEX idx_global_session_key (global_session_key),
    INDEX idx_timestamp (timestamp),
    INDEX idx_turns_context_number (context_id, turn_number),
    FOREIGN KEY (context_id) REFERENCES contexts(context_id) ON DELETE CASCADE,
    FOREIGN KEY (global_session_key) REFERENCES sessions(global_session_key) ON DELETE CASCADE
);
```

---

## 5. 환경변수 설정

### 필수 환경변수

```bash
# Redis 연결 (필수)
REDIS_URL=rediss://default:password@host:port/0

# MariaDB 연결 (필수, Sprint 4+)
MARIADB_HOST=my-mariadb.mariadb.svc.cluster.local
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=ChangeMe!
MARIADB_DATABASE=session_manager
```

### 선택 환경변수

```bash
# Mock 모드 (테스트/로컬용, 기본 false)
USE_MOCK_REDIS=false

# MariaDB 사용 여부 (기본 true)
USE_MARIADB=true

# MariaDB 연결 풀 설정
MARIADB_POOL_SIZE=10
MARIADB_MAX_OVERFLOW=20
MARIADB_POOL_RECYCLE=3600
MARIADB_ECHO=false

# TTL 설정 (초 단위, 기본 600)
SESSION_CACHE_TTL=600
SESSION_MAP_TTL=600

# API Key 인증 (기본 false)
ENABLE_API_KEY_AUTH=false
```

---

## 6. 주요 변경사항 요약

### 필드명 통일

| Sprint 3              | Sprint 4          | 설명                    |
|------------------------|-------------------|-------------------------|
| `session_id`           | 제거됨            | Redis 중복 필드 제거     |
| `local_session_key`    | `agent_session_key` | 모든 코드에서 통일      |
| `current_subagent_id`  | `action_owner`    | MariaDB 필드명 통일      |
| `last_updated_at`      | `updated_at`      | MariaDB 필드명 통일      |

### 저장소 구조

| 저장소 | 역할           | 저장 시점 | 저장 내용                    |
|--------|----------------|-----------|------------------------------|
| Redis  | 동기 캐시      | 즉시      | 세션/컨텍스트/턴 메타데이터   |
| MariaDB| 비동기 영구 저장| 응답 후   | 세션/Agent 매핑/턴 메타데이터 |

### 코드 품질 개선 (리팩토링)

- **공통 유틸리티 함수 도입** (`app/core/utils.py`):
  - `safe_json_parse()`: JSON 파싱 통일 및 안전한 에러 처리
  - `safe_json_dumps()`: JSON 직렬화 통일
  - `datetime_to_iso()`, `iso_to_datetime()`: Datetime 변환 통일
  - `safe_datetime_parse()`: Datetime 파싱 통일
- **코드 중복 제거**: 중복된 JSON 파싱 로직을 유틸리티 함수로 통일
- **타입 힌팅 개선**: 함수 반환 타입 명시 및 타입 안정성 향상
- **에러 처리 일관성 향상**: 안전한 파싱 및 변환으로 런타임 에러 방지
- **필드명 통일**: Context Repository에서 `last_updated_at` → `updated_at` 통일
- **인터페이스 제거**: `app/repositories/base.py` 삭제, Duck Typing 방식으로 전환
  - ABC 패턴 인터페이스 제거 (`SessionRepositoryInterface`, `ContextRepositoryInterface`, `ProfileRepositoryInterface`)
  - 실제 구현과 맞지 않는 인터페이스 제거로 코드 단순화
  - Duck Typing을 통한 런타임 유연성 확보 (`hasattr`, `isinstance` 체크)
- **사용되지 않는 스키마 제거**: `app/schemas/contexts.py` 정리
  - `ContextCreate`, `ContextUpdate`, `ContextResponse` 제거 (사용되지 않음)
  - `TurnCreate`, `TurnCreateWithAPI` 제거 (사용되지 않음)
  - 실제 사용 중인 스키마만 유지: `TurnResponse`, `SolApiResultRequest`, `SessionFullResponse`, `SolDBSTransactionPayload`, `SolDBSTransactionResult`

---

## 7. 향후 개선 사항 (다음 스프린트)

### API 경로 구조 개선

현재 구조에서는 Contexts API가 세션 관련 기능을 포함하고 있어 경로 일관성이 부족합니다. 다음 스프린트에서 다음과 같이 개선 예정입니다:

**현재 구조 (Sprint 4)**:
- `POST /api/v1/contexts/turn-results` - SOL API 결과 저장
- `GET /api/v1/contexts/sessions/{global_session_key}/full` - 세션 전체 정보 조회

**개선 예정 구조 (Sprint 5+)**:
- `POST /api/v1/sessions/{global_session_key}/turns` - 턴 메타데이터 저장
- `GET /api/v1/sessions/{global_session_key}/full` - 세션 + 턴 목록 조회

**개선 이유**:
1. **경로 일관성**: 세션 관련 기능을 `/sessions` 하위로 통합
2. **RESTful 설계**: 리소스 계층 구조 명확화 (Session → Turn)
3. **API 이해도 향상**: 세션과 턴의 관계가 경로에서 명확히 드러남

> **참고**: 현재 API는 이미 배포되어 있어 하위 호환성을 위해 Sprint 4에서는 유지합니다.

---

## 8. 참고 문서

- `docs/Session_Manager_API_Sprint3.md` – Sprint 3 API 명세서
- `docs/SPRINT3_DESIGN_FINAL.md` – 설계 문서
- `docs/session_manager_onprem_migration.md` – 배포 가이드
- `scripts/init_db.sql` – MariaDB 스키마 초기화 스크립트

---

**작성일**: 2026년 1월 14일  
**버전**: v4.0 (Sprint 4)  
**작성자**: Session Manager Team
