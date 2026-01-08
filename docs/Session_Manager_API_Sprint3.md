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
    - 공통 Contexts API로 정리:
      - `POST /api/v1/contexts`
      - `GET /api/v1/contexts/{context_id}`
      - `PATCH /api/v1/contexts/{context_id}`
      - `POST /api/v1/contexts/{context_id}/turns`
      - `GET /api/v1/contexts/{context_id}/turns`
      - `GET /api/v1/contexts/{context_id}/turns/{turn_id}`

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
  "user_id": "user_001",
  "channel": "app",
  "request_id": "req_20260108_0001",
  "device_info": {
    "os": "iOS",
    "app_version": "1.0.0"
  }
}
```

| 필드        | 타입    | 필수 | 설명                                                         |
|-------------|---------|------|--------------------------------------------------------------|
| user_id     | string  | ✅   | 사용자 ID                                                   |
| channel     | string  | ✅   | 채널 (예: `web`, `app`, `kiosk`, `ivr`)                     |
| request_id  | string  | ❌   | 호출 추적용 ID (로깅/분석 용도)                             |
| device_info | object  | ❌   | 디바이스/클라이언트 정보 (자유 형식 JSON)                  |

> Sprint 2와 달리 **요청에 `customer_profile`는 받지 않습니다.**  
> 개인화 프로파일은 **배치가 프로파일 DB에 저장**해 두고, SM은 여기서 **조회만** 합니다.

**Response Body – `SessionCreateResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "context_id": "ctx_20260108_ijkl9012",
  "session_state": "start",
  "is_new": true,
  "created_at": "2026-01-08T09:00:00Z",
  "expires_at": "2026-01-08T10:00:00Z",
  "customer_profile": {
    "user_id": "user_001",
    "attributes": [],
    "segment": "VIP",
    "preferences": {
      "marketing_opt_in": true
    }
  }
}
```

| 필드               | 타입    | 설명                                                                 |
|--------------------|---------|----------------------------------------------------------------------|
| global_session_key | string  | 세션 전체를 대표하는 **글로벌 세션 ID**                             |
| context_id         | string  | 컨텍스트/턴 메타데이터를 묶는 ID                                     |
| session_state      | string  | 세션 상태 (`start` / `talk` / `end` 등)                             |
| is_new             | bool    | 새로 생성된 세션인지 (`true`) / 기존 세션 재사용인지 (`false`)      |
| created_at         | string  | 세션 생성 시각 (ISO8601)                                            |
| expires_at         | string  | 세션 만료 예정 시각 (TTL 기반)                                      |
| customer_profile   | object  | 개인화 프로파일 스냅샷 (없으면 `null`)                              |

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
GET /api/v1/sessions/gsess_20260108_abcd1234?channel=app&agent_type=task&agent_id=transfer_agent
```

| 파라미터  | 타입                  | 필수 | 설명                                                                |
|-----------|-----------------------|------|---------------------------------------------------------------------|
| channel   | string                | ❌   | 채널 (주로 로깅/분석용; 생략 가능)                                 |
| agent_type| `AgentType` enum      | ❌   | Agent 유형 (`task`/`knowledge` 등, 업무 Agent면 보통 `task`)       |
| agent_id  | string                | ❌   | Agent ID (예: `transfer_agent`, `dbs_caller`)                       |

**Response Body – `SessionResolveResponse` (예시)**

```json
{
  "global_session_key": "gsess_20260108_abcd1234",
  "agent_session_key": "asess_transfer_001",
  "conversation_id": "conv_20260108_efgh5678",
  "context_id": "ctx_20260108_ijkl9012",
  "session_state": "talk",
  "is_first_call": false,
  "task_queue_