# API 인터페이스 정의

## 1. 전체 API 목록

| IF-ID | API Name | Source | Target | Integration Type | Mode | Request | Response | 비고 |
|-------|----------|--------|--------|------------------|------|---------|----------|------|
| PORTAL-SM-MGR-01 | ListConversationsByPeriod | Portal | Session Manager | Sync | Real-time | admin_id, from_datetime, to_datetime, cursor(optional), limit(optional), filters(optional) | success, data{items[], cursor_next, total_count}, error{code, message} | 포털 관리자가 기간 조건으로 대화이력 "목록(메타)" 조회 |
| PORTAL-SM-MGR-02 | GetConversationDetail | Portal | Session Manager | Sync | Real-time | admin_id, conversation_id, cursor(optional), limit(optional) | success, data{conversation_id, session_id, items[], cursor_next}, error{code, message} | 특정 conversation_id의 대화 상세(턴/메시지/이력) 조회 |
| PORTAL-SM-MGR-03 | DeleteConversationHistory | Portal | Session Manager | Sync | Real-time | admin_id, conversation_id, reason(optional) | success, data{conversation_id, deleted}, error{code, message} | 특정 conversation_id 대화이력 삭제 |
| AGW-SM-01 | EnqueueTask | Master Agent | Session Manager | Sync | Real-time | session_id, conversation_id, turn_id, intent, priority, session_state, task_payload | status(accepted), task_id | 마스터가 의도/우선순위 기반으로 SM의 Task Queue에 실행 작업을 적재 |
| AGW-SM-02 | GetTaskStatus | Master Agent | Session Manager | Sync | Real-time | task_id | task_id, task_status, progress(optional), updated_at | 마스터(또는 GW)가 task_id로 비동기 실행 상태 조회 |
| AGW-SM-03 | GetTaskResult | Master Agent | Session Manager | Sync | Real-time | task_id | task_id, task_status(end), outcome, response_text(optional), result_payload(optional) | 마스터(또는 GW)가 task_id로 비동기 실행 결과 조회 |
| AGW-SM-04 | ResolveSession | Master Agent | Session Manager | Sync | Real-time | session_key, channel, conversation_id(optional), user_id_ref(optional) | session_id, conversation_id, session_state, is_first_call, customer_profile_ref(optional) | MA가 세션을 조회/생성하고 현재 상태/최초호출/프로파일 참조를 획득 |
| AGW-SM-05 | PatchSessionState | Master Agent | Session Manager | Sync | Real-time | session_id, conversation_id, turn_id, session_state, state_patch | status, updated_at | MA가 슬롯/스텝/세션상태를 갱신(continue/end 반영 포함) |
| AGW-SM-06 | CreateInitialSession | Agent GW | Session Manager | Sync | Real-time | user_id, channel, session_key{scope, key}, request_id | session_key{scope, key}, request_id, session_id, conversation_id, session_state(start), expires_at | AGW가 최초 진입 시 초기 세션을 생성(또는 발급) |

---

## 2. API 상세 명세

### 2.1 Portal - Session Manager 인터페이스

#### PORTAL-SM-MGR-01: ListConversationsByPeriod

**API 설명**
- 포털 관리자가 기간 조건으로 대화이력 목록(메타데이터)을 조회
- 페이징 및 필터링 지원

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| admin_id | string | ✅ | 관리자 ID |
| from_datetime | datetime | ✅ | 조회 시작 시간 (ISO 8601) |
| to_datetime | datetime | ✅ | 조회 종료 시간 (ISO 8601) |
| cursor | string | ❌ | 페이징 커서 (다음 페이지 조회 시) |
| limit | integer | ❌ | 페이지당 조회 개수 (기본값: 50) |
| filters | object | ❌ | 필터 조건 (user_id, channel, session_id) |

**Response**

```json
{
  "success": true/false,
  "data": {
    "items": [
      {
        "conversation_id": "string",
        "session_id": "string",
        "user_id": "string",
        "channel": "string",
        "started_at": "datetime",
        "last_turn_at": "datetime",
        "status": "string"
      }
    ],
    "cursor_next": "string",
    "total_count": "integer"
  },
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| success | boolean | 요청 성공 여부 |
| data.items[] | array | 대화 목록 |
| data.items[].conversation_id | string | 대화 ID |
| data.items[].session_id | string | 세션 ID |
| data.items[].user_id | string | 사용자 ID |
| data.items[].channel | string | 채널 (web, mobile, app 등) |
| data.items[].started_at | datetime | 대화 시작 시간 |
| data.items[].last_turn_at | datetime | 마지막 턴 시간 |
| data.items[].status | string | 대화 상태 (active, ended) |
| data.cursor_next | string | 다음 페이지 커서 |
| data.total_count | integer | 전체 대화 수 |
| error.code | string | 에러 코드 |
| error.message | string | 에러 메시지 |

---

#### PORTAL-SM-MGR-02: GetConversationDetail

**API 설명**
- 특정 conversation_id의 대화 상세 내용을 조회
- 턴별 메시지 이력 포함 (마스킹 처리됨)

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| admin_id | string | ✅ | 관리자 ID |
| conversation_id | string | ✅ | 대화 ID |
| cursor | string | ❌ | 페이징 커서 |
| limit | integer | ❌ | 페이지당 턴 개수 (기본값: 100) |

**Response**

```json
{
  "success": true/false,
  "data": {
    "conversation_id": "string",
    "session_id": "string",
    "items": [
      {
        "turn_id": "string",
        "role": "user/assistant",
        "text_masked": "string",
        "created_at": "datetime",
        "outcome": "string",
        "sa_status": "string"
      }
    ],
    "cursor_next": "string"
  },
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| success | boolean | 요청 성공 여부 |
| data.conversation_id | string | 대화 ID |
| data.session_id | string | 세션 ID |
| data.items[] | array | 대화 턴 목록 |
| data.items[].turn_id | string | 턴 ID |
| data.items[].role | enum | 발화자 (user, assistant) |
| data.items[].text_masked | string | 마스킹 처리된 메시지 텍스트 |
| data.items[].created_at | datetime | 메시지 생성 시간 |
| data.items[].outcome | string | 처리 결과 (normal, fallback 등) |
| data.items[].sa_status | string | Sub Agent 처리 상태 |
| data.cursor_next | string | 다음 페이지 커서 |
| error.code | string | 에러 코드 |
| error.message | string | 에러 메시지 |

---

#### PORTAL-SM-MGR-03: DeleteConversationHistory

**API 설명**
- 특정 conversation_id의 대화 이력을 삭제
- GDPR 등 개인정보 삭제 요청 처리용

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| admin_id | string | ✅ | 관리자 ID |
| conversation_id | string | ✅ | 삭제할 대화 ID |
| reason | string | ❌ | 삭제 사유 |

**Response**

```json
{
  "success": true/false,
  "data": {
    "conversation_id": "string",
    "deleted": true/false
  },
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| success | boolean | 요청 성공 여부 |
| data.conversation_id | string | 삭제된 대화 ID |
| data.deleted | boolean | 삭제 성공 여부 |
| error.code | string | 에러 코드 |
| error.message | string | 에러 메시지 |

---

### 2.2 Master Agent - Session Manager 인터페이스

#### AGW-SM-01: EnqueueTask

**API 설명**
- Master Agent가 의도 분석 결과를 기반으로 Task Queue에 작업을 적재
- 우선순위 기반 작업 스케줄링 지원
- 비동기 작업 실행을 위한 Task ID 발급

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| session_id | string | ✅ | 세션 ID |
| conversation_id | string | ✅ | 대화 ID |
| turn_id | string | ✅ | 턴 ID |
| intent | string | ✅ | 의도 분류 결과 |
| priority | integer | ✅ | 작업 우선순위 (1-10) |
| session_state | enum | ✅ | 세션 상태 (start, talk, end) |
| task_payload | object | ✅ | 작업 페이로드 (마스킹 처리됨) |

**Response**

```json
{
  "status": "accepted",
  "task_id": "string"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| status | string | 작업 수락 상태 (accepted) |
| task_id | string | 작업 추적용 고유 ID |

---

#### AGW-SM-02: GetTaskStatus

**API 설명**
- Task ID로 비동기 작업의 현재 실행 상태를 조회
- 폴링 방식으로 작업 진행 상황 확인

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| task_id | string | ✅ | 작업 ID |

**Response**

```json
{
  "task_id": "string",
  "task_status": "undefined/continue/end",
  "progress": "integer",
  "updated_at": "datetime"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| task_id | string | 작업 ID |
| task_status | enum | 작업 상태 (undefined: 대기/처리중, continue: 계속 진행, end: 완료) |
| progress | integer | 작업 진행률 (0-100, optional) |
| updated_at | datetime | 상태 업데이트 시간 |

---

#### AGW-SM-03: GetTaskResult

**API 설명**
- 완료된 작업의 최종 결과를 조회
- task_status가 'end'인 경우에만 호출 가능

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| task_id | string | ✅ | 작업 ID |

**Response**

```json
{
  "task_id": "string",
  "task_status": "end",
  "outcome": "normal/fallback/continue",
  "response_text": "string",
  "result_payload": "object"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| task_id | string | 작업 ID |
| task_status | string | 작업 상태 (end 고정) |
| outcome | enum | 처리 결과 (normal: 정상 완료, fallback: 대체 처리, continue: 계속 진행) |
| response_text | string | 응답 텍스트 (optional) |
| result_payload | object | 결과 데이터 (optional) |

---

#### AGW-SM-04: ResolveSession

**API 설명**
- Master Agent가 세션을 조회하거나 생성
- Global/Local 세션 구분 및 현재 상태 파악
- 최초 호출 여부 및 고객 프로파일 참조 획득

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| session_key | enum | ✅ | 세션 키 타입 (global, local) |
| channel | string | ✅ | 채널 정보 (web, mobile, app 등) |
| conversation_id | string | ❌ | 대화 ID (optional) |
| user_id_ref | string | ❌ | 사용자 ID 참조 (optional) |

**Response**

```json
{
  "session_id": "string",
  "conversation_id": "string",
  "session_state": "start/talk/end",
  "is_first_call": true/false,
  "customer_profile_ref": "string"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| session_id | string | 세션 ID (조회 또는 신규 생성) |
| conversation_id | string | 대화 ID |
| session_state | enum | 세션 상태 (start: 시작, talk: 진행중, end: 종료) |
| is_first_call | boolean | 최초 호출 여부 |
| customer_profile_ref | string | 고객 프로파일 참조 ID (optional) |

---

#### AGW-SM-05: PatchSessionState

**API 설명**
- Master Agent가 세션 상태를 업데이트
- 슬롯, 스텝, 세션 상태 갱신
- Continue/End 상태 반영

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| session_id | string | ✅ | 세션 ID |
| conversation_id | string | ✅ | 대화 ID |
| turn_id | string | ✅ | 턴 ID |
| session_state | enum | ✅ | 세션 상태 (start, talk, end) |
| state_patch | object | ✅ | 상태 패치 데이터 (step, slots, flags) |

**state_patch 구조**

```json
{
  "step": "string",
  "slots": {
    "slot_name": "slot_value"
  },
  "flags": {
    "flag_name": true/false
  }
}
```

**Response**

```json
{
  "status": "success/error",
  "updated_at": "datetime"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| status | enum | 업데이트 결과 (success, error) |
| updated_at | datetime | 업데이트 시간 |

---

### 2.3 Agent Gateway - Session Manager 인터페이스

#### AGW-SM-06: CreateInitialSession

**API 설명**
- Agent Gateway가 사용자 최초 진입 시 초기 세션을 생성
- Global Session Key 발급
- 세션 만료 시간 설정

**Request Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| user_id | string | ✅ | 사용자 ID |
| channel | string | ✅ | 채널 정보 (web, mobile, app 등) |
| session_key | object | ✅ | 세션 키 정보 {scope, key} |
| session_key.scope | string | ✅ | 세션 스코프 (global) |
| session_key.key | string | ✅ | 세션 키 값 |
| request_id | string | ✅ | 요청 추적용 ID |

**Response**

```json
{
  "session_key": {
    "scope": "global",
    "key": "string"
  },
  "request_id": "string",
  "session_id": "string",
  "conversation_id": "string",
  "session_state": "start",
  "expires_at": "datetime"
}
```

**Response Fields**

| 필드 | 타입 | 설명 |
|------|------|------|
| session_key.scope | string | 세션 스코프 (global) |
| session_key.key | string | 세션 키 값 |
| request_id | string | 요청 추적용 ID |
| session_id | string | 생성된 세션 ID |
| conversation_id | string | 생성된 대화 ID |
| session_state | string | 세션 상태 (start 고정) |
| expires_at | datetime | 세션 만료 시간 |
