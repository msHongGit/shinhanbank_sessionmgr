# Session Manager API 명세 (Sprint 5 기준)

> **Sprint 5 구현 기준** – Redis 전용 전환, MariaDB 선택적 통합, API 통합, 구조 단순화  
> **Session Manager 역할**: 세션/컨텍스트/프로파일 메타데이터 저장 및 조회 (Redis 필수, MariaDB 선택적)

---

## 0. Sprint 4 문서와 무엇이 달라졌나?

이 문서는 기존 [docs/Session_Manager_API_Sprint4.md](Session_Manager_API_Sprint4.md) 기준에서 **Sprint 5 실제 코드**에 맞게 정리한 버전입니다.

### 주요 변경사항

#### 1. Redis 전용 전환 (MariaDB 선택적)
- **Sprint 4**: Redis (동기) + MariaDB (비동기) 하이브리드 저장소
- **Sprint 5**: Redis 필수, MariaDB 선택적
  - Redis: 세션/턴 메타데이터 및 프로파일 저장 (필수)
  - MariaDB: 배치 프로파일 조회용 (선택적, MARIADB_HOST 설정 시에만 사용)
  - BackgroundTasks 제거 (비동기 저장 로직 제거)
  - 모든 데이터를 Redis에 동기 저장

#### 2. API 통합
- **Sprint 4**: `/sessions`와 `/contexts` 분리
- **Sprint 5**: 모든 API를 `/sessions`로 통합
  - `POST /api/v1/contexts/turn-results` → `POST /api/v1/sessions/{global_session_key}/api-results`
  - `GET /api/v1/contexts/sessions/{key}/full` → `GET /api/v1/sessions/{global_session_key}/full`

#### 3. `context_id` 제거
- **Sprint 4**: `context_id`를 별도로 관리
- **Sprint 5**: `context_id` 완전 제거
  - `global_session_key`만 사용하여 세션과 턴 관리
  - 세션과 턴의 관계가 1:N으로 단순화

#### 4. Agent 매핑 구조 변경
- **Sprint 4**: 별도 Redis 키 `session_map:{global_session_key}:{agent_id}` 사용
- **Sprint 5**: 세션 hash 내부에 `agent_mappings` 필드로 통합 저장
  - `session:{global_session_key}` hash의 `agent_mappings` 필드에 JSON 문자열로 저장
  - 구조: `{"agent_id": {"agent_session_key": "...", "agent_type": "..."}}`

#### 5. SOL API 필드명 변경
- **Sprint 4**: `sessionId` 필드 사용 (camelCase)
- **Sprint 5**: `global_session_key` 필드 사용 (snake_case)
  - 다른 API와 일관성 유지를 위해 snake_case로 통일
  - `turn_id`도 동일하게 snake_case로 통일

#### 6. Repository 통합
- **Sprint 4**: `RedisSessionRepository`와 `RedisContextRepository` 분리
- **Sprint 5**: Turn 관련 기능을 `RedisSessionRepository`로 통합
  - `add_turn`, `get_turns`, `delete_turns` 메서드가 `RedisSessionRepository`에 포함

#### 7. Mock Repository 정리
- **Sprint 4**: Session/Context/Profile Mock 모두 존재
- **Sprint 5**: Profile Mock만 유지 (개발/테스트용)

#### 8. Task Queue 함수 제거
- **Sprint 4**: Task Queue 관련 Redis 함수 존재 (`enqueue_task`, `dequeue_task` 등)
- **Sprint 5**: Task Queue 관련 함수 완전 제거
  - Session Manager는 Task Queue를 관리하지 않음
  - Master Agent가 Task Queue를 관리하고 Session Manager에 상태만 업데이트

#### 9. JWT 토큰 기반 인증 추가
- **Sprint 4**: API Key 기반 인증 (선택적)
- **Sprint 5**: JWT 토큰 기반 인증으로 전환
  - 세션 생성 시 `access_token`, `refresh_token`, `jti` 자동 발급
  - Access Token 만료 시간: 300초 (5분)
  - Refresh Token 만료 시간: 330초 (5분 30초)
  - Refresh Token Rotation 적용 (토큰 갱신 시 새 `jti` 생성)
  - Refresh Token 갱신 시 세션 TTL 연장 (사용자 활동의 일부로 간주)
  - 토큰 검증 API (`/api/v1/sessions/verify`) 추가
  - 토큰 갱신 API (`/api/v1/sessions/refresh`) 추가
  - Ping API 경로 변경 (`/{global_session_key}/ping` → `/ping`, 토큰 기반)
  - 세션 종료 API 경로 변경 (`/{global_session_key}` → `/`, 토큰 기반)

#### 10. TTL 설정 변경
- **Sprint 4**: 기본 TTL 600초 (10분)
- **Sprint 5**: 기본 TTL 300초 (5분)

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

### 1.2 인증 (JWT 토큰 기반)

Session Manager는 JWT 토큰 기반 인증을 사용합니다.

#### 토큰 발급
- 세션 생성 시 `access_token`과 `refresh_token`이 자동 발급됩니다.
- `access_token`: Access Token (만료 시간: 300초 = 5분)
- `refresh_token`: Refresh Token (만료 시간: 330초 = 5분 30초)
- `jti`: JWT ID (UUID, Redis에 `jti:{jti}` → `global_session_key` 매핑 저장)

#### 토큰 사용 방법
- **헤더**: `Authorization: Bearer {access_token}` 또는 `Authorization: Bearer {refresh_token}`
- **쿠키**: `access_token={access_token}` 또는 `refresh_token={refresh_token}`

#### 토큰 검증
- 모든 JWT 토큰은 `JWT_SECRET_KEY`로 서명되어 있습니다.
- 토큰 검증 실패 시 401 Unauthorized 반환

#### Refresh Token Rotation
- 토큰 갱신 시 새로운 `jti`가 생성되고, 기존 `jti` 매핑은 삭제됩니다.
- 이전 Refresh Token은 더 이상 사용할 수 없습니다.

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
- 이때 Session Manager가:
  - `global_session_key` 자동 발급 (응답에 포함)
  - JWT 토큰 자동 발급 (`access_token`, `refresh_token`, `jti`)
  - **Redis에 즉시 저장** (동기)
  - 참고: 프로파일은 세션 생성 시점에는 조회하지 않음 (CUSNO 없음)

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
  "global_session_key": "gsess_20260108_abcd1234",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

| 필드               | 타입   | 설명                                                             |
|--------------------|--------|------------------------------------------------------------------|
| global_session_key | string | 세션 전체를 대표하는 **글로벌 세션 ID** (이후 모든 호출에 사용) |
| access_token       | string | Access Token (JWT, 만료 시간: 5분)                               |
| refresh_token      | string | Refresh Token (JWT, 만료 시간: 6분)                             |
| jti                | string | JWT ID (UUID, Redis에 `jti:{jti}` → `global_session_key` 매핑 저장) |

**저장 흐름**

1. Redis에 즉시 저장 (동기) → API 응답 반환

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
  "customer_profile": null,
  "batch_profile": {
    "daily": {
      "CUSNO": "0616001905",
      "STD_DT": "20260121",
      ...
    },
    "monthly": {
      "CUSNO": "0616001905",
      "STD_YM": "202601",
      ...
    }
  },
  "realtime_profile": {
    "cusnoN10": "0616001905",
    "cusSungNmS20": "홍길동",
    "hpNoS12": "01031286270",
    ...
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

1. Redis에서 세션 조회
2. `reference_information` 파싱하여 상위 필드로 추출
3. Agent 매핑 조회 (세션 hash의 `agent_mappings` 필드에서)
4. 프로파일 조회:
   - 세션의 `cusno` 필드 확인 (실시간 프로파일 저장 시 저장된 값)
   - `cusno`가 있으면 Redis에서 `profile:realtime:{cusno}`, `profile:batch:{cusno}` 조회
   - `cusno`가 없으면 프로파일 없음 (실시간 프로파일 저장 전)

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
2. **Invoke 시 TTL 연장**: `session_state`가 `talk`로 변경될 때 세션 TTL 연장 (Sliding Expiration on Invoke)
3. Agent 세션 매핑 저장 (`agent_session_key` + `last_agent_id`가 있을 때):
   - 세션 hash의 `agent_mappings` 필드에 JSON 문자열로 저장

**TTL 연장 시점**
- **Invoke 시** (`session_state = "talk"`): 세션 TTL 연장 (사용자 메시지 전송 시)
- **Refresh Token 갱신 시**: 세션 TTL 연장 (사용자 활동의 일부로 간주)
- **Ping 시**: TTL 연장 안 함 (단순 생존 확인만)

---

### 2.4 세션 종료

#### 2.4.1 세션 종료 (내부 서비스용 - global_session_key 경로)

**Endpoint**

```http
DELETE /api/v1/sessions/{global_session_key}
```

**Query Parameters**

| 파라미터     | 타입   | 필수 | 설명     |
|--------------|--------|------|----------|
| close_reason | string | ❌   | 종료 사유 |

**언제 사용하나?**

- Master Agent가 세션을 종료할 때
- 내부 서비스에서 `global_session_key`를 알고 있을 때

**Response Body**

```json
{
  "status": "success",
  "closed_at": "2026-01-14T10:35:00Z",
  "archived_conversation_id": "arch_gsess_20260108_abcd1234"
}
```

#### 2.4.2 세션 종료 (토큰 기반)

**Endpoint**

```http
DELETE /api/v1/sessions
```

**Query Parameters**

| 파라미터     | 타입   | 필수 | 설명     |
|--------------|--------|------|----------|
| close_reason | string | ❌   | 종료 사유 |

**언제 사용하나?**

- Client/AGW가 세션을 종료할 때
- 토큰에서 `global_session_key`를 추출하여 세션 종료

**요청**
- 헤더: `Authorization: Bearer {access_token}` 또는 쿠키의 `access_token`

**Response Body**

```json
{
  "status": "success",
  "closed_at": "2026-01-14T10:35:00Z",
  "archived_conversation_id": "arch_gsess_20260108_abcd1234"
}
```

**저장 흐름**

1. 토큰에서 `global_session_key` 추출
2. Redis에 세션 상태를 `end`로 업데이트 (동기)
3. `jti` 매핑 삭제

---

### 2.5 세션 생존 확인 (Ping)

**Endpoint**

```http
GET /api/v1/sessions/ping
```

**언제 사용하나?**

- Client/AGW가 세션 생존 여부를 확인할 때
- 토큰에서 `global_session_key`를 추출하여 세션 확인
- **TTL 연장 없음** (Refresh Token으로 TTL 연장)

**요청**
- 헤더: `Authorization: Bearer {access_token}` 또는 쿠키의 `access_token`

**Response Body**

```json
{
  "is_alive": true,
  "expires_at": "2026-01-14T10:45:00Z"
}
```

| 필드       | 타입    | 설명                                    |
|------------|---------|-----------------------------------------|
| is_alive   | boolean | 세션 존재 여부 (false면 세션이 없거나 만료됨) |
| expires_at | string  | 현재 만료 시각 (is_alive=false이면 null)     |

**주의사항**
- TTL 연장을 하지 않습니다. TTL 연장이 필요하면 Refresh Token API를 사용하세요.

---

### 2.6 토큰 갱신

**Endpoint**

```http
POST /api/v1/sessions/refresh
```

**언제 사용하나?**

- Access Token이 만료되었을 때 Refresh Token으로 새 토큰 발급
- 세션 TTL도 함께 연장됨 (사용자 활동의 일부로 간주)

**요청**
- 헤더: `Authorization: Bearer {refresh_token}` 또는 쿠키의 `refresh_token`
- 또는 요청 body에 `refresh_token` 포함

**Response Body**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "global_session_key": "gsess_20260108_abcd1234",
  "jti": "de8a2b69-48b5-4f72-bbae-09903954f5fe"
}
```

| 필드               | 타입   | 설명                                                             |
|--------------------|--------|------------------------------------------------------------------|
| access_token       | string | 새 Access Token (JWT, 만료 시간: 5분)                            |
| refresh_token      | string | 새 Refresh Token (JWT, 만료 시간: 6분, Refresh Token Rotation)   |
| global_session_key | string | Global 세션 키 (AGW에만 전달)                                    |
| jti                | string | 새 JWT ID (UUID, 기존 jti 매핑 삭제 후 새로 생성)                |

**처리 로직**
1. Refresh Token 검증 및 jti 추출
2. Redis에서 `jti:{jti}` → `global_session_key` 조회
3. **세션 TTL 연장** (`session:{global_session_key}` TTL 갱신, 사용자 활동의 일부로 간주)
4. 새 jti 생성 (Refresh Token Rotation)
5. 새 Access Token 및 Refresh Token 발급
6. 기존 jti 매핑 삭제 및 새 jti 매핑 저장 (TTL: 5분)

**주의사항**
- Refresh Token Rotation: 기존 Refresh Token은 무효화되고 새 Refresh Token이 발급됩니다.
- 세션 TTL 연장: 토큰 갱신 시 세션 TTL도 함께 연장됩니다 (5분).

---

### 2.7 실시간 API 연동 결과 저장

**Endpoint**

```http
POST /api/v1/sessions/{global_session_key}/api-results
```

**언제 사용하나?**

- SOL API (`/api/v1/sol/transaction`, `/api/v1/sol/transaction/result`) 호출 결과를 저장할 때
- 실시간 API 연동 로그를 턴 메타데이터로 저장

**Request Body – `SolApiResultRequest`**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "turn_id": "turn_002",
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
| global_session_key| string | ✅   | 세션 ID (`global_session_key`)            |
| turn_id           | string | ✅   | 턴 ID                                   |
| agent             | string | ❌   | Agent ID                                |
| result             | string | ❌   | 결과 상태 (`SUCCESS` / `FAILURE` 등)     |
| transactionResult | array  | ❌   | SOL API 트랜잭션 결과 배열               |

**Response Body – `TurnResponse`**

```json
{
  "turn_id": "turn_002",
  "global_session_key": "gsess_20260108_abcd1234",
  "turn_number": null,
  "role": null,
  "agent_id": null,
  "agent_type": null,
  "metadata": {
    "sol_api": {
      "global_session_key": "gsess_20260108_abcd1234",
      "turn_id": "turn_002",
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
| turn_id           | string | 턴 ID (요청의 turn_id)                  |
| global_session_key| string | 글로벌 세션 키                           |
| metadata          | object | 메타데이터 (sol_api 블록 포함)           |
| timestamp         | string | 저장 시각 (ISO 8601 형식)               |

**저장 흐름**

1. Redis에 턴 메타데이터 저장 (동기)
   - `turns:{global_session_key}` 리스트에 JSON 문자열로 추가

---

### 2.8 세션 전체 정보 조회

**Endpoint**

```http
GET /api/v1/sessions/{global_session_key}/full
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
      "global_session_key": "gsess_20260108_abcd1234",
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
      "global_session_key": "gsess_20260108_abcd1234",
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
2. Redis에서 턴 목록 조회 (`turns:{global_session_key}`)
3. 통합하여 응답 반환

---

## 3. 저장소 구조

### 3.1 Redis (단일 저장소)

**세션 정보**

- 키: `session:{global_session_key}`
- 타입: Hash
- 필드:
  - `global_session_key`: 세션 키
  - `user_id`: 사용자 ID (세션 생성 시 전달한 임시값)
  - `cusno`: 고객번호 (실시간 프로파일 저장 시 cusnoN10에서 추출하여 저장)
  - `channel`: 채널 정보 (JSON 문자열)
  - `conversation_id`: 대화 ID
  - `session_state`: 세션 상태
  - `task_queue_status`: Task Queue 상태
  - `subagent_status`: SubAgent 상태
  - `action_owner`: 현재 액션 담당자
  - `reference_information`: 멀티턴 컨텍스트 (JSON 문자열)
  - `turn_ids`: 턴 ID 목록 (JSON 문자열)
  - `profile`: 프로파일 (JSON 문자열)
  - `customer_profile`: 고객 프로파일 스냅샷 (제거됨, 사용 안 함)
  - 프로파일은 Redis에 별도 저장: `profile:realtime:{cusno}`, `profile:batch:{cusno}` (cusno는 세션의 cusno 필드 값)
  - `start_type`: 세션 진입 유형
  - `cushion_message`: 쿠션 메시지
  - `session_attributes`: 세션 속성 (JSON 문자열)
  - `last_event`: 마지막 이벤트 (JSON 문자열)
  - `agent_mappings`: Agent 세션 매핑 (JSON 문자열, `{"agent_id": {"agent_session_key": "...", "agent_type": "..."}}`)
  - `close_reason`: 종료 사유
  - `final_summary`: 최종 요약
  - `ended_at`: 종료 시각
  - `expires_at`: 만료 시각
  - `created_at`: 생성 시각
  - `updated_at`: 업데이트 시각
- TTL: `SESSION_CACHE_TTL` (기본 300초)

**턴 목록**

- 키: `turns:{global_session_key}`
- 타입: List
- 값: 턴 메타데이터 (JSON 문자열)
- TTL: 세션과 동일 (세션 TTL에 따라 자동 만료)

**JWT 토큰 매핑**

- 키: `jti:{jti}`
- 타입: String
- 값: `global_session_key`
- TTL: `SESSION_CACHE_TTL` (기본 300초)
- 용도: JWT ID (`jti`)로 `global_session_key` 조회
- 참고: Refresh Token Rotation 시 기존 `jti` 매핑은 삭제되고 새 `jti` 매핑이 생성됨

**프로파일 저장소**

- 실시간 프로파일:
  - 키: `profile:realtime:{cusno}` (cusno는 실시간 프로파일의 cusnoN10 값)
  - 타입: String (JSON 문자열)
  - TTL: 없음 (영구 저장)
  - 저장 시점: 실시간 프로파일 업데이트 API 호출 시
  - 저장 흐름: 실시간 프로파일에서 cusnoN10 추출 → 세션에 cusno 필드 저장 → Redis에 프로파일 저장

- 배치 프로파일:
  - 키: `profile:batch:{cusno}` (cusno는 실시간 프로파일의 cusnoN10 값)
  - 타입: String (JSON 문자열)
  - TTL: 없음 (영구 저장)
  - 저장 시점: 실시간 프로파일 업데이트 API 호출 시 (MariaDB에서 조회하여 저장)
  - 저장 흐름: 실시간 프로파일 저장 시 MariaDB에서 배치 프로파일 조회 → Redis에 저장

- 프로파일 조회:
  - 세션 조회 시 세션의 `cusno` 필드로 프로파일 조회
  - `cusno`가 없으면 프로파일 없음 (실시간 프로파일 저장 전)

---

## 4. 환경변수 설정

### 필수 환경변수

```bash
# Redis 연결 (필수)
REDIS_URL=rediss://default:password@host:port/0
```

### 선택 환경변수

```bash
# TTL 설정 (초 단위, 기본 300)
SESSION_CACHE_TTL=300

# JWT 설정
JWT_SECRET_KEY=your-secret-key-here  # 암호학적으로 안전한 랜덤 문자열 (예: openssl rand -hex 32)
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=300  # Access Token 만료 시간 (초, 기본값: 300초 = 5분)
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=330 # Refresh Token 만료 시간 (초, 기본값: 330초 = 5분 30초)

# MariaDB 설정 (선택적, 배치 프로파일 조회용)
MARIADB_HOST=my-mariadb.mariadb.svc.cluster.local  # MariaDB 호스트 (비어있으면 MariaDB 연결 안 함)
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=ChangeMe!
MARIADB_DATABASE=session_manager
MARIADB_POOL_SIZE=10
MARIADB_MAX_OVERFLOW=20
```

---

## 5. 주요 변경사항 요약

### Sprint 4 → Sprint 5 변경사항

| 항목 | Sprint 4 | Sprint 5 | 설명 |
|------|----------|----------|------|
| 저장소 | Redis + MariaDB | Redis 필수, MariaDB 선택적 | MariaDB는 배치 프로파일 조회용으로만 사용 |
| 저장 방식 | 동기(Redis) + 비동기(MariaDB) | 동기(Redis)만 | BackgroundTasks 제거 |
| API 구조 | `/sessions` + `/contexts` | `/sessions` 통합 | 모든 API를 `/sessions`로 통합 |
| `context_id` | 존재 | 제거 | `global_session_key`만 사용 |
| Agent 매핑 | 별도 키 `session_map:{key}:{agent_id}` | 세션 hash 내부 `agent_mappings` | 구조 단순화 |
| SOL 필드명 | `sessionId` (camelCase) | `global_session_key` (snake_case) | 다른 API와 일관성 유지 |
| Repository | Session + Context 분리 | Session에 통합 | Turn 기능 통합 |
| Mock | Session/Context/Profile | Profile만 | Mock 정리 |
| 인증 | API Key 기반 | JWT 토큰 기반 | JWT 토큰 발급/검증/갱신 |
| TTL 설정 | 기본 600초 | 기본 300초 | TTL 단축 |

### 코드 품질 개선 (리팩토링)

- **MariaDB 선택적 통합**: 배치 프로파일 조회용으로만 사용
  - `app/db/mariadb.py`: MariaDB 연결 관리 (MARIADB_HOST 설정 시에만 초기화)
  - `app/repositories/mariadb_batch_profile_repository.py`: 배치 프로파일 조회용
  - MariaDB 연결 정보가 없어도 서비스 정상 동작 (배치 프로파일만 None 반환)
- **API 통합**: `/contexts` 엔드포인트를 `/sessions`로 통합
  - `app/api/v1/contexts.py` 삭제
  - `app/api/v1/sessions.py`에 통합
- **Repository 통합**: Turn 관련 기능을 Session Repository로 통합
  - `app/repositories/redis_context_repository.py` 삭제
  - `app/repositories/redis_session_repository.py`에 통합
- **Mock 정리**: Profile Mock만 유지
  - `app/repositories/mock/mock_session_repository.py` 삭제
  - `app/repositories/mock/mock_context_repository.py` 삭제
  - `app/repositories/mock/mock_profile_repository.py` 유지
- **Task Queue 함수 제거**: 사용하지 않는 Task Queue 관련 함수 제거
  - `app/db/redis.py`에서 `enqueue_task`, `dequeue_task` 등 제거
- **인터페이스 제거**: `app/repositories/base.py` 삭제, Duck Typing 방식으로 전환
- **스키마 통합**: `app/schemas/contexts.py` 삭제, `app/schemas/common.py`로 통합
- **JWT 토큰 인증 추가**: API Key 인증 제거, JWT 토큰 기반 인증으로 전환
  - `app/core/jwt.py`: JWT 토큰 생성/검증 유틸리티
  - `app/core/jwt_auth.py`: JWT 인증 의존성
  - 세션 생성 시 JWT 토큰 자동 발급
  - 토큰 검증, 갱신, Ping API 추가
- **API Key 인증 제거**: `app/core/auth.py` 삭제, 모든 API Key 관련 설정 제거

---

## 6. 향후 개선 사항 (다음 스프린트)

### 여러 Agent 매핑 한 번에 처리

현재 구조에서는 한 번의 PATCH 요청에 하나의 Agent만 등록할 수 있습니다. 다음 스프린트에서 다음과 같이 개선 예정입니다:

**현재 구조 (Sprint 5)**:
- `state_patch.agent_session_key` + `state_patch.last_agent_id`로 하나의 Agent만 등록

**개선 예정 구조 (Sprint 6+)**:
- `state_patch.agent_mappings` 배열로 여러 Agent를 한 번에 등록 가능

**개선 이유**:
1. **효율성**: 여러 Agent를 한 번에 등록하여 네트워크 요청 감소
2. **원자성**: 여러 Agent 매핑을 한 번에 처리하여 일관성 보장
3. **편의성**: Master Agent가 여러 Agent를 동시에 등록할 때 편리

---

## 7. 참고 문서

- `docs/Session_Manager_API_Sprint4.md` – Sprint 4 API 명세서
- `docs/Session_Manager_API_Sprint3.md` – Sprint 3 API 명세서
- `docs/redis_data.md` – Redis 데이터 구조 정의서
- `docs/redis.md` – Redis 운영 가이드

---

**작성일**: 2026년 1월 14일  
**버전**: v5.0 (Sprint 5)  
**작성자**: Session Manager Team
