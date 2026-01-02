# Session Manager API 명세 (Sprint 2)

> **Sprint 2 구현 기준** - Mock Repository 기반  
> **Session Manager 역할**: API 제공 (Passive) - 요청을 받아 응답만 함  
> **세션 키 전략**: Session Manager가 Global Session Key 자동 생성하여 반환 (`gsess_{timestamp}_{uuid}`)  
> **Local Session Key**: Sprint 3+ 구현 예정

---

## 🌐 환경별 Base URL

| 환경 | Base URL | 비고 |
|------|----------|------|
| **로컬 개발** | `http://localhost:8000` | `uv run uvicorn app.main:app` |
| **Docker 로컬** | `http://localhost:8000` | `docker run -p 8000:8000` |
| **Azure Dev** | `https://session-manager-dev.shinhan.azure.com` | AKS + Ingress |
| **Azure Prod** | `https://session-manager.shinhan.azure.com` | Production |

### 예시 호출 (환경별)

```bash
# 로컬 개발
curl http://localhost:8000/health

# Azure Dev
curl https://session-manager-dev.shinhan.azure.com/health

# Azure Prod
curl https://session-manager.shinhan.azure.com/health
```

### 인증 (API Key)

⚠️ **Sprint 2 Dev/Demo 환경**: API 키 인증이 **기본 비활성화**되어 있습니다 (`ENABLE_API_KEY_AUTH=false`).  
운영 환경 전환 시에는 `.env`에서 `ENABLE_API_KEY_AUTH=true`로 설정하고 각 호출자별 API 키를 반드시 구성해야 합니다.

| 환경 | AGW API Key | MA API Key | 관리 위치 |
|------|------------|-----------|----------|
| **로컬/테스트** | (비활성화) | (비활성화) | `.env`에서 `ENABLE_API_KEY_AUTH=false` |
| **Azure Dev** | Kubernetes Secret | Kubernetes Secret | `session-manager-secrets` |
| **Azure Prod** | Key Vault | Key Vault | Azure Key Vault 관리 |

```bash
# Dev 환경 API Key 확인
kubectl get secret session-manager-secrets -n shinhan-dev \
  -o jsonpath='{.data.AGW_API_KEY}' | base64 -d
```

### 데이터 저장소

| Sprint | 저장소 | 데이터 지속성 | 비고 |
|--------|--------|-------------|------|
| **Sprint 2** | Redis (+ 부분 Mock) | ⚠️ Redis 재시작 시 세션 데이터 초기화 가능 | 세션/컨텍스트/Local 세션 매핑은 Redis, 그 외 미이관 데이터는 Mock 사용 |
| **Sprint 3+** (예정) | Redis + PostgreSQL | ✅ 영구 저장 | Prod부터 전체 영구 저장소 전환 |

⚠️ **중요**
- Sprint 2 기준으로 **Session/Context/Local Session Mapping은 Redis에 저장**합니다.
- 아직 Redis로 옮기지 않은 데이터(예: 일부 프로파일 Mock 데이터)는 **In-Memory Mock Repository**를 계속 사용합니다.

### Redis 연동 개요 (Session Manager)

Session Manager는 Redis를 다음 시점에 사용합니다.

- **세션 상태 (Session)**
  - 키: `session:{global_session_key}` (Hash)
  - 사용 시점:
    - `POST /api/v1/agw/sessions` : 세션 생성/재사용 시 세션 Hash 저장 또는 조회
    - `GET /api/v1/ma/sessions/resolve` : 세션 조회 시 Hash 조회
    - `PATCH /api/v1/ma/sessions/state` : 세션 상태 업데이트 시 Hash 필드 업데이트
    - `POST /api/v1/ma/sessions/close` : 세션 종료 시 상태/요약 정보 업데이트

- **Global↔Local 세션 매핑**
  - 키: `session_map:{global_session_key}:{agent_id}` (Hash)
  - 사용 시점:
    - `POST /api/v1/ma/sessions/local` : Local 세션 등록 시 매핑 Hash 저장
    - `GET /api/v1/ma/sessions/local` : Local 세션 조회 시 매핑 Hash 조회
    - `POST /api/v1/ma/sessions/close` : 세션 종료 시 Global 세션 기준 매핑 삭제 예정 (Sprint 3+ 확장)

- **대화 컨텍스트 및 턴 이력**
  - Context 메타데이터: 키 `context:{context_id}` (Hash)
  - 턴 이력: 키 `context_turns:{context_id}` (List)
  - 사용 시점:
    - `POST /api/v1/agw/sessions` : 세션 생성 시 초기 Context 메타데이터 생성
    - `POST /api/v1/ma/context/turn` : 턴 추가 시 List에 Append, Context `last_updated_at` 갱신
    - `GET /api/v1/ma/context/history` : 대화 이력 조회 시 List 전체 조회
    - `DELETE /api/v1/portal/context/{context_id}` : Context 및 턴 이력 삭제

💡 **Task Queue용 Redis 키(`task_queue:*`)는 Master Agent용이며, Session Manager는 현재 사용하지 않습니다.**

---

## 📋 Session Manager 특징

### ✅ Session Manager는 API를 제공하는 서버입니다
- **수동적(Passive) 역할**: 외부 시스템의 요청을 받아 응답만 제공
- **능동적 호출 없음**: Session Manager가 다른 시스템(AGW, MA, SA)을 호출하지 않음
- **상태 저장소**: 세션, 컨텍스트, 프로파일 데이터를 저장하고 조회만 담당

### 🔄 통신 방향
```
AGW  ──(요청)──▶ Session Manager ──(응답)──▶ AGW
MA   ──(요청)──▶ Session Manager ──(응답)──▶ MA
Portal ─(요청)──▶ Session Manager ──(응답)──▶ Portal
VDB  ──(요청)──▶ Session Manager ──(응답)──▶ VDB
```

**Session Manager는 절대로 외부 시스템을 호출하지 않습니다.**

---

## 🗂️ API 목록 (Sprint 2)

| Category | Method | Endpoint | Caller | 설명 |
|----------|--------|----------|--------|------|
| **AGW - 세션** | POST | `/api/v1/agw/sessions` | AGW | 초기 세션 생성 |
| **MA - 세션** | GET | `/api/v1/ma/sessions/resolve` | MA | 세션 조회 |
| | POST | `/api/v1/ma/sessions/local` | MA | Local 세션 등록 (업무 Agent용) |
| | GET | `/api/v1/ma/sessions/local` | MA | Local 세션 조회 |
| | PATCH | `/api/v1/ma/sessions/state` | MA | 세션 상태 업데이트 |
| | POST | `/api/v1/ma/sessions/close` | MA | 세션 종료 |
| **MA - 대화** | GET | `/api/v1/ma/context/history` | MA | 대화 이력 조회 |
| | POST | `/api/v1/ma/context/turn` | MA | 대화 턴 저장 |
| **MA - 프로파일** | GET | `/api/v1/ma/profiles/{user_id}` | MA | 고객 프로파일 조회 |
| **Batch** | POST | `/api/v1/batch/profiles` | VDB | 프로파일 배치 업로드 |
| **Portal** | GET | `/api/v1/portal/sessions` | Portal | 세션 목록 조회 (읽기 전용) |
| | GET | `/api/v1/portal/context/{context_id}` | Portal | Context 정보 조회 |
| | DELETE | `/api/v1/portal/context/{context_id}` | Portal | Context 삭제 |

---

## 1. AGW → Session Manager

### 1.1 세션 생성

**Endpoint**: `POST /api/v1/agw/sessions`  
**설명**: Agent GW가 초기 세션을 생성합니다. Session Manager가 Global Session Key를 자동 생성하여 반환합니다.  
👉 **Demo 시연 구조에서는 AGW가 분리되어 있지 않으며, Master Agent(MA, Guardrail 포함)가 이 API를 직접 호출하여 세션을 생성합니다.**  
**인증**: `X-API-Key: {AGW_API_KEY}` (Sprint 2 dev/demo에서는 비활성화)

**Request Body**:
```json
{
  "user_id": "user_vip_001",                           // 필수
  "channel": "web",                                    // 필수
  "device_info": {                                      // 옵션 (데모용)
    "device_type": "desktop",
    "os": "macOS",
    "browser": "Chrome"
  }
  // "request_id": "req_20260101_001"                  // 옵션 (추적용, 데모에서는 생략)
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| user_id | string | ✅ | 사용자 ID |
| channel | string | ✅ | 채널 (web, mobile, kiosk) |
| device_info | object | ❌ | 디바이스 정보 (옵션) |
| request_id | string | ❌ | 요청 추적 ID (옵션) |
| customer_profile | object | ❌ | 고객 개인화 프로파일 스냅샷 (`CustomerProfile` 스키마, Demo 시 세션과 함께 전달) |

**Response** (201 Created):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "session_id": "sess_001",
  "context_id": "ctx_001",
  "session_state": "start",
  "is_new": true,
  "created_at": "2026-01-01T10:00:00Z",
  "expires_at": "2026-01-01T11:00:00Z"
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| global_session_key | string | 글로벌 세션 키 (UUID 기반) |
| session_id | string | 세션 ID (내부 ID) |
| context_id | string | Context ID (대화 이력 ID) |
| session_state | string | 세션 상태 (start/active/end) |
| is_new | boolean | 신규 세션 여부 |
| created_at | datetime | 생성 시간 (ISO 8601) |
| expires_at | datetime | 만료 시간 (1시간 후) |
| customer_profile | object | 세션에 저장된 고객 프로파일 (`CustomerProfile`) |

**에러 응답**:
```json
{
  "detail": "User profile not found"
}
```

---

## 2. MA → Session Manager (세션 관리)

### 2.1 세션 조회

**Endpoint**: `GET /api/v1/ma/sessions/resolve`  
**설명**: MA가 세션 정보를 조회합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| channel | string | ❌ | 채널 (옵션, 데모에서는 포함하지만 선택적) |
| agent_type | string | ❌ | Agent 유형 (task/business) |
| agent_id | string | ❌ | Agent ID (업무 Agent용) |

**Request Example**:
```http
GET /api/v1/ma/sessions/resolve?global_session_key=gsess_20260101_uuid_001&channel=web
X-API-Key: ma-api-key
```

**Response** (200 OK):
```json
{
  "session": {
    "global_session_key": "gsess_20260101_uuid_001",
    "session_id": "sess_001",
    "user_id": "user_vip_001",
    "channel": "web",
    "session_state": "active",
    "subagent_status": "continue",
    "last_event": "skill_matched",
    "created_at": "2026-01-01T10:00:00Z",
    "updated_at": "2026-01-01T10:05:00Z",
    "expires_at": "2026-01-01T11:00:00Z"
  },
  "context": {
    "context_id": "ctx_001",
    "turn_count": 3
  },
  "local_session": null
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| global_session_key | string | 글로벌 세션 키 |
| local_session_key | string/null | Local 세션 키 (업무 Agent용) |
| conversation_id | string | 세션에 연결된 대화 ID |
| context_id | string | 세션에 연결된 Context ID |
| session_state | string | 세션 상태 (start/talk/end) |
| is_first_call | boolean | 세션 상태가 `start` 인지 여부 |
| task_queue_status | string | Task Queue 상태 (null/notnull) |
| subagent_status | string | SubAgent 상태 (undefined/continue/end) |
| last_event | object/null | 마지막 이벤트 (`LastEvent`) |
| customer_profile | object/null | 세션에 연결된 고객 프로파일 (`CustomerProfile`) |

---

### 2.2 Local 세션 등록 (업무 Agent용)

**Endpoint**: `POST /api/v1/ma/sessions/local`  
**설명**: 업무 Agent Start 후 Local 세션을 등록합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Request Body**:
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "agent_id": "sa_exchange",
  "local_session_key": "local_sess_exchange_001",
  "agent_type": "business"
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| agent_id | string | ✅ | Agent ID |
| local_session_key | string | ✅ | Local 세션 키 (업무 Agent가 발급) |
| agent_type | string | ✅ | Agent 유형 (business) |

**Response** (201 Created):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "agent_id": "sa_exchange",
  "local_session_key": "local_sess_exchange_001",
  "registered_at": "2026-01-01T10:10:00Z"
}
```

---

### 2.3 Local 세션 조회

**Endpoint**: `GET /api/v1/ma/sessions/local`  
**설명**: Global 세션 키로 Local 세션 키를 조회합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| agent_id | string | ✅ | Agent ID |

**Request Example**:
```http
GET /api/v1/ma/sessions/local?global_session_key=gsess_20260101_uuid_001&agent_id=sa_exchange
X-API-Key: ma-api-key
```

**Response** (200 OK):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "agent_id": "sa_exchange",
  "local_session_key": "local_sess_exchange_001",
  "registered_at": "2026-01-01T10:10:00Z"
}
```

---

### 2.4 세션 상태 업데이트

**Endpoint**: `PATCH /api/v1/ma/sessions/state`  
**설명**: MA가 세션 상태를 업데이트합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Request Body**:
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "session_state": "active",
  "subagent_status": "end",
  "last_event": "task_completed"
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| session_state | string | ❌ | 세션 상태 (start/active/end) |
| subagent_status | string | ❌ | SubAgent 상태 (undefined/continue/end) |
| last_event | string | ❌ | 마지막 이벤트 |

**Response** (200 OK):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "session_state": "active",
  "subagent_status": "end",
  "updated_at": "2026-01-01T10:15:00Z"
}
```

---

### 2.5 세션 종료

**Endpoint**: `POST /api/v1/ma/sessions/close`  
**설명**: 세션을 종료합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Request Body**:
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "reason": "user_request"
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| reason | string | ❌ | 종료 사유 |

**Response** (200 OK):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "session_state": "end",
  "closed_at": "2026-01-01T10:20:00Z",
  "local_sessions_deleted": 1
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| global_session_key | string | 글로벌 세션 키 |
| session_state | string | 세션 상태 (end) |
| closed_at | datetime | 종료 시간 |
| local_sessions_deleted | integer | 삭제된 Local 세션 수 |

---

## 3. MA → Session Manager (대화 이력)

### 3.1 대화 이력 조회

**Endpoint**: `GET /api/v1/ma/context/history`  
**설명**: MA가 대화 이력을 조회합니다 (Talk 요청 시 사용).  
**인증**: `X-API-Key: {MA_API_KEY}`

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| context_id | string | ❌ | Context ID (없으면 세션에서 조회) |

**Request Example**:
```http
GET /api/v1/ma/context/history?global_session_key=gsess_20260101_uuid_001
X-API-Key: ma-api-key
```

**Response** (200 OK):
```json
{
  "context_id": "ctx_001",
  "turn_count": 3,
  "turns": [
    {
      "turn_number": 1,
      "role": "user",
      "content": "환율 1400원 이상일 때 100만원 환전해줘",
      "timestamp": "2026-01-01T10:01:00Z"
    },
    {
      "turn_number": 2,
      "role": "assistant",
      "content": "스킬 탐색이 완료되었습니다.",
      "timestamp": "2026-01-01T10:02:00Z"
    },
    {
      "turn_number": 3,
      "role": "assistant",
      "content": "100만원을 환전하였습니다.",
      "timestamp": "2026-01-01T10:03:00Z"
    }
  ]
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| context_id | string | Context ID |
| turn_count | integer | 총 턴 수 |
| turns[] | array | 대화 턴 목록 |
| turns[].turn_number | integer | 턴 번호 (1부터 시작) |
| turns[].role | string | 발화자 (user/assistant) |
| turns[].content | string | 발화 내용 |
| turns[].timestamp | datetime | 발화 시간 |

---

### 3.2 대화 턴 저장

**Endpoint**: `POST /api/v1/ma/context/turn`  
**설명**: MA가 대화 턴을 저장합니다.  
**인증**: `X-API-Key: {MA_API_KEY}`

**Request Body**:
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "context_id": "ctx_001",
  "role": "user",
  "content": "환율 1400원 이상일 때 100만원 환전해줘",
  "metadata": {
    "intent": "exchange_currency_conditional"
  }
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| global_session_key | string | ✅ | 글로벌 세션 키 |
| context_id | string | ❌ | Context ID (없으면 세션에서 조회) |
| role | string | ✅ | 발화자 (user/assistant) |
| content | string | ✅ | 발화 내용 |
| metadata | object | ❌ | 메타데이터 (intent, entity 등) |

**Response** (201 Created):
```json
{
  "context_id": "ctx_001",
  "turn_number": 1,
  "turn_id": "turn_001",
  "saved_at": "2026-01-01T10:01:00Z"
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| context_id | string | Context ID |
| turn_number | integer | 턴 번호 |
| turn_id | string | 턴 ID |
| saved_at | datetime | 저장 시간 |

---

## 4. MA → Session Manager (프로파일)

### 4.1 고객 프로파일 조회

**Endpoint**: `GET /api/v1/ma/profiles/{user_id}`  
**설명**: MA가 고객 프로파일을 조회합니다 (Start 요청 시 사용).  
**인증**: `X-API-Key: {MA_API_KEY}`

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| user_id | string | ✅ | 사용자 ID |

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| attribute_keys | array[string] | ❌ | 조회할 속성 키 목록 (필터링) |

**Request Example**:
```http
GET /api/v1/ma/profiles/user_vip_001?attribute_keys=tier&attribute_keys=preferred_language
X-API-Key: ma-api-key
```

**Response** (200 OK):
```json
{
  "user_id": "user_vip_001",
  "attributes": {
    "tier": "VIP",
    "preferred_language": "ko",
    "name": "홍길동",
    "email": "hong@example.com"
  },
  "updated_at": "2025-12-31T00:00:00Z"
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| user_id | string | 사용자 ID |
| attributes | object | 프로파일 속성 (key-value) |
| updated_at | datetime | 마지막 업데이트 시간 |

---

## 5. VDB → Session Manager (배치)

### 5.1 프로파일 배치 업로드

**Endpoint**: `POST /api/v1/batch/profiles`  
**설명**: VDB에서 고객 프로파일을 배치로 업로드합니다.  
**인증**: `X-API-Key: {VDB_API_KEY}`

**Request Body**:
```json
{
  "profiles": [
    {
      "user_id": "user_001",
      "attributes": {
        "tier": "NORMAL",
        "preferred_language": "ko"
      }
    },
    {
      "user_id": "user_vip_001",
      "attributes": {
        "tier": "VIP",
        "preferred_language": "ko",
        "name": "홍길동"
      }
    }
  ]
}
```

**Request Fields**:
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| profiles[] | array | ✅ | 프로파일 목록 |
| profiles[].user_id | string | ✅ | 사용자 ID |
| profiles[].attributes | object | ✅ | 프로파일 속성 (key-value) |

**Response** (200 OK):
```json
{
  "total": 2,
  "success": 2,
  "failed": 0,
  "processed_at": "2026-01-01T09:00:00Z"
}
```

**Response Fields**:
| 필드 | 타입 | 설명 |
|------|------|------|
| total | integer | 총 프로파일 수 |
| success | integer | 성공 건수 |
| failed | integer | 실패 건수 |
| processed_at | datetime | 처리 시간 |

---

## 6. Portal → Session Manager (관리)

### 6.1 세션 목록 조회 (읽기 전용)

**Endpoint**: `GET /api/v1/portal/sessions`  
**설명**: Portal에서 세션 목록을 조회합니다 (읽기 전용).  
**인증**: `X-API-Key: {PORTAL_API_KEY}`

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| page | integer | ❌ | 페이지 번호 (기본값: 1) |
| page_size | integer | ❌ | 페이지 크기 (기본값: 20, 최대: 100) |
| user_id | string | ❌ | 사용자 ID 필터 |
| session_state | string | ❌ | 세션 상태 필터 (start/active/end) |

**Request Example**:
```http
GET /api/v1/portal/sessions?page=1&page_size=20&session_state=active
X-API-Key: portal-api-key
```

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "global_session_key": "gsess_20260101_uuid_001",
      "session_id": "sess_001",
      "user_id": "user_vip_001",
      "channel": "web",
      "session_state": "active",
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-01T10:15:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

### 6.2 Context 정보 조회

**Endpoint**: `GET /api/v1/portal/context/{context_id}`  
**설명**: Context(대화 이력) 정보를 조회합니다.  
**인증**: `X-API-Key: {PORTAL_API_KEY}`

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| context_id | string | ✅ | Context ID |

**Request Example**:
```http
GET /api/v1/portal/context/ctx_001
X-API-Key: portal-api-key
```

**Response** (200 OK):
```json
{
  "context_id": "ctx_001",
  "session_id": "sess_001",
  "turn_count": 3,
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-01T10:03:00Z"
}
```

---

### 6.3 Context 삭제

**Endpoint**: `DELETE /api/v1/portal/context/{context_id}`  
**설명**: Context(대화 이력)를 삭제합니다 (세션은 유지).  
**인증**: `X-API-Key: {PORTAL_API_KEY}`

**Path Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| context_id | string | ✅ | Context ID |

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| reason | string | ❌ | 삭제 사유 |

**Request Example**:
```http
DELETE /api/v1/portal/context/ctx_001?reason=user_request
X-API-Key: portal-api-key
```

**Response** (200 OK):
```json
{
  "context_id": "ctx_001",
  "deleted": true,
  "deleted_at": "2026-01-01T10:30:00Z"
}
```

---

## 🔒 인증 (API Key)

모든 API는 `X-API-Key` 헤더로 인증합니다.

| Caller | API Key 환경변수 | 예시 값 |
|--------|------------------|---------|
| AGW | `AGW_API_KEY` | `agw-api-key` |
| MA | `MA_API_KEY` | `ma-api-key` |
| Portal | `PORTAL_API_KEY` | `portal-api-key` |
| VDB | `VDB_API_KEY` | `vdb-api-key` |

**인증 실패 시**:
```json
{
  "detail": "Invalid or missing API Key"
}
```

---

## 📊 에러 코드

| HTTP Status | 설명 | 예시 |
|-------------|------|------|
| 200 OK | 성공 | 조회 성공 |
| 201 Created | 생성 성공 | 세션 생성, 턴 저장 |
| 400 Bad Request | 잘못된 요청 | 필수 파라미터 누락 |
| 401 Unauthorized | 인증 실패 | API Key 없음/잘못됨 |
| 404 Not Found | 리소스 없음 | 세션/프로파일 없음 |
| 500 Internal Server Error | 서버 오류 | DB 연결 실패 등 |

**에러 응답 형식**:
```json
{
  "detail": "Session not found"
}
```

---

## 🎯 Session Manager 핵심 원칙

### ✅ Session Manager는 **절대로** 다른 시스템을 호출하지 않습니다

```
❌ Session Manager → AGW (호출 안 함)
❌ Session Manager → MA (호출 안 함)
❌ Session Manager → SA (호출 안 함)
❌ Session Manager → Portal (호출 안 함)

✅ AGW/MA/Portal/VDB → Session Manager (요청)
✅ Session Manager → AGW/MA/Portal/VDB (응답만)
```

### Session Manager의 책임
1. ✅ **세션 저장소**: 세션 생성, 조회, 상태 업데이트, 종료
2. ✅ **대화 이력 저장소**: 턴별 대화 저장 및 조회
3. ✅ **프로파일 저장소**: 고객 프로파일 저장 및 조회
4. ✅ **API 제공**: 외부 시스템의 요청에 응답만 제공

### Session Manager가 하지 않는 것
- ❌ 외부 시스템 호출 (AGW, MA, SA, Portal 등)
- ❌ 비즈니스 로직 처리 (의도 분류, 스킬 탐색 등)
- ❌ 능동적인 알림 (Webhook, Notification 등)

---

**Sprint 2 API 명세 완료!** 🎉
