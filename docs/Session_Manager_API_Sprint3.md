# Session Manager API 명세 (Sprint 3 기준)

> **Sprint 3 구현 기준** – Unified Sessions + Contexts/Turns, 텍스트 미저장  
> **Session Manager 역할**: 세션/컨텍스트/프로파일 메타데이터 저장 및 조회 (Passive)

---

## 0. Sprint 2 문서와 무엇이 달라졌나?

이 문서는 기존 [docs/Session_Manager_API_Sprint2.md](docs/Session_Manager_API_Sprint2.md) 기준에서 **Sprint 3 실제 코드**에 맞게 정리한 버전입니다.

  "is_first_call": false
- **통합 세션 API**
  - Sprint 2:
    - `POST /api/v1/agw/sessions`
    - `GET /api/v1/ma/sessions/resolve`
    - `POST /api/v1/ma/sessions/close`
    - `POST /api/v1/ma/sessions/local` 등 **호출자별 별도 엔드포인트**
  - Sprint 3:
    - **단일 세션 API**로 통합
    - `POST /api/v1/sessions` – 세션 생성
    - `GET /api/v1/sessions/{global_session_key}` – 세션 조회
    - `PATCH /api/v1/sessions/{global_session_key}/state` – 세션 상태 업데이트
    - `DELETE /api/v1/sessions/{global_session_key}` – 세션 종료

- **Local 세션 키 → Agent 세션 키**
  - Sprint 2: `local_session_key`
  - Sprint 3: **외부 계약 필드명 `agent_session_key`** 로 통일  
    (내부 Redis 구현에만 `local_session_key` 흔적 존재 가능)

- **턴(대화 이력) 설계 변경**
  - Sprint 2:
    - 대화 텍스트(`content`)를 SM에 저장 (`/ma/context/turn`, `/ma/context/history`)
  - Sprint 3:
    - **대화 텍스트 미저장 원칙**
    - `/api/v1/contexts/{context_id}/turns` 는 **메타데이터만** 저장 (event_type, intent, 외부 API 결과 등)
    - 텍스트는 MA/외부 시스템이 관리

- **Contexts API 정리**
  - Sprint 2: `/api/v1/ma/context/turn`, `/api/v1/ma/context/history` 등 MA 전용
  - Sprint 3:
    - **Context CRUD/조회 API 제거**
    - 세션/컨텍스트는 여전히 Redis에 저장되지만, 외부에서 직접 Context를 생성/조회하는 API는 제공하지 않음
    - 대신 **SOL 실시간 API 연동 결과 저장 전용 단일 API**만 제공:
      - `POST /api/v1/contexts/turn-results` – `session_id`/`turn_id` 기반으로 SOL `/api/v1/sol/transaction` + `/api/v1/sol/transaction/result` 요청/응답 전체를 턴 메타데이터로 저장

- **세션 종료 동작**
  - Sprint 2 문서: "모든 Local 세션 매핑 삭제, Task Queue 정리" 라고 설명
  - Sprint 3 코드: **실제 구현은 세션 상태만 `end`로 변경**  
    (매핑/Task Queue 정리는 향후 별도 컴포넌트에서 담당 예정)

- **인증(API Key)**
  - 설계는 동일하게 `X-API-Key` 기반이나,
  - Sprint 3 개발 단계에서는 **sessions/contexts 라우터에서 API Key 의존성 제거**  
    → 로컬/테스트에서 인증 없이 호출 가능  
    → 운영 전환 시 `require_api_key` 복구 예정

---

## 1. 공통 정보

### 1.1 베이스 URL (예시)

| 환경           | Base URL                               | 비고                           |
|----------------|-----------------------------------------|--------------------------------|
| 로컬 개발      | `http://localhost:8000`                | `uv run uvicorn app.main:app` |
| Docker 로컬    | `http://localhost:8000`                | `docker run -p 8000:8000`     |
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

> 현재 Sprint 3 개발 브랜치에서는 `sessions`, `contexts` 라우터에 `require_api_key` 의존성이 제거되어 있어, 로컬/Dev에서는 인증 없이 호출 가능합니다.  
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
 - 이미 같은 세션이 살아 있다면 **기존 세션 재사용** (`is_new=false`)
- 이때 Session Manager가:
  - `global_session_key`, `context_id` 자동 발급  
    (내부적으로 `conversation_id`도 생성하지만 응답에는 포함하지 않음)
  - 프로파일 저장소에서 개인화 프로파일 조회 후 응답에 포함 (있다면)

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

> Sprint 3 구현에서는 **요청에 `customer_profile` 를 받지 않습니다.**  
> 개인화 프로파일은 **외부 Profile Repository(DB)** 에 저장되어 있고, Session Manager는 여기서 **조회만** 합니다.

**Response Body – `SessionCreateResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234"
}
```

| 필드               | 타입   | 설명                                                             |
|--------------------|--------|------------------------------------------------------------------|
| global_session_key | string | 세션 전체를 대표하는 **글로벌 세션 ID** (이후 모든 호출에 사용) |

---

### 2.2 세션 조회

**Endpoint**

```http
GET /api/v1/sessions/{global_session_key}
```

**언제 사용하나?**

- MA가 세션 상태/마지막 이벤트/Agent 매핑 등을 조회할 때
- Portal/Client가 세션 상세를 읽을 때
- 업무 Agent가 본인의 `agent_session_key` 를 SM에서 resolve 할 때

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
  "session_state": "start",
  "is_first_call": true,
  "task_queue_status": "null",
  "subagent_status": "undefined",
  "last_event": null,
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
    "skill_tag": "balance_inquiry",
    "skillset_metadata": {
      "agent": "skillset-agent",
      "skill": "계좌조회"
    }
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
  "turn_count": 1
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
| active_task               | object	null | DirectRouting용 활성 태스크 정보 (`reference_information.active_task`)      |
| conversation_history      | array	null  | 최근 대화 이력 (`reference_information.conversation_history`)               |
| current_intent            | string	null | 현재 활성 의도 (`reference_information.current_intent`)                     |
| current_task_id           | string	null | 현재 태스크 ID (`reference_information.current_task_id`)                    |
| task_queue_status_detail  | array	null  | 태스크 큐 상세 상태 (`reference_information.task_queue_status`)            |
| turn_count                | integer	null | 대화 턴 수 (`reference_information.turn_count`)                             |