# Session Manager 시연 시나리오 (Sprint 2)

> **Sprint 2 기준** - Mock Repository 기반 구현  
> **Demo 구조**: Demo UI (Client + Portal 통합) → Master Agent(MA, Guardrail 포함) → SK → SA Mock API  
> **핵심**: MA가 세션 생성 요청 시 Session Manager가 Global Session Key 자동 생성 및 세션 객체 관리 (Local Key는 Sprint 3+)

---

## 📋 주요 시나리오 예시 (Session Manager API 포함)

### 1. 환전 시나리오

1. 세션 생성 (POST /api/v1/agw/sessions)
2. 세션 조회 (GET /api/v1/ma/sessions/resolve)
3. 대화 턴 저장 (POST /api/v1/ma/context/turn)
4. MA 전처리/의도분류/스킬매칭/최종응답 (동의어, PII, 금칙어 포함)
5. 대화 턴 저장 (어시스턴트)
6. 세션 종료 (POST /api/v1/ma/sessions/close)

각 시나리오의 MA 처리 예시:
- 동의어 치환: "환전해줘"→"환전하다", "유효한지 확인해줘"→"유효성 검사", "잔액 알려줘"→"잔액 조회" 등
- 개인정보(PII) 탐지: 카드번호/계좌번호 등
- 금칙어: 예시에서는 없음
- 의도분류/스킬매칭/최종응답: intent, skill, message, metadata 등 포함

**시나리오**: 환율 조건부 환전 업무 
**참여 컴포넌트**: Client → AGW → Session Manager → Demo UI → Master Agent(MA, Guardrail 포함) → SK/SA Mock API  
**Session Manager 역할**: 세션/컨텍스트/프로파일 관리만  
**세션 키 전략** (Sprint 2):
- **Global Session Key**: Session Manager가 자동 생성 (`gsess_{timestamp}_{uuid}`)
- **Local Session Key**: 미구현 (Sprint 3+에서 업무 Agent별 매핑 추가)

**대화 예시**: "환율 1400원 이상일 때 100만원 환전해줘"

### Sprint 2 Demo 구조

**현재 (Sprint 2 Demo)**:
- **Demo UI** (Client + Portal 통합 화면):
  - 채팅 입력/응답 표시 (Client 역할)
  - 전처리/의도분류/스킬 매칭 결과 패널 (Portal 역할)
  - Direct Routing 모드 전환 (Sprint 2에서는 SA 선택 UI는 없음)

- **Master Agent (MA)**:
  - Guardrail 모듈 포함 (전처리, 금칙어/PII, 필터링)
  - 의도분류, 스킬셋 매칭, SA 호출 모두 담당
  - Session Manager API 호출자(AGW 역할까지 포함)

**향후 (Sprint 3+)**:
- Client와 Portal이 별도 시스템으로 분리 (Demo UI → Client + Portal 분리)

**Sprint 2 제약사항**:
- Sub Agent 미구현 → **SA Mock API 별도 구현 필요**
- SA 응답 경로: **SA Mock API → MA → Client**
- **Global Session Key만 사용** (Local Session Key는 Sprint 3+에서 구현)
- **Session Manager가 Global Session Key 자동 생성**

---

## 🎯 시연 목표

1. ✅ Session Manager 세션 생성/조회 기능 확인
2. ✅ 대화 이력 저장 및 조회 기능 확인
3. ✅ **Client에서 채팅 입력 및 SA 선택 확인**
4. ✅ **Portal에서 전처리/의도분류/스킬 탐색 결과 모니터링 확인**
5. ✅ **Skill Set 연동을 통한 스킬 탐색 확인**
6. ✅ **SA Mock API → MA → Client 응답 경로 확인** (채팅 응답)
7. ✅ **Direct Routing 시나리오 확인**

---

## 🔄 시스템 흐름도

```
┌────────────────────────── 실제 경로 (상용 기준) ───────────────────────────┐
│                                                                          │
│ Client → AGW → Session Manager → AGW → Client                            │
│                             │                                           │
│                             └────────→ Master Agent → SK/SA → Client    │
└──────────────────────────────────────────────────────────────────────────┘

┌────────────────────────── Sprint 2 Demo 구조 ────────────────────────────┐
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                              Demo UI                               │  │
│  │  - 세션 키 생성 (Client 역할)                                      │  │
│  │  - 채팅 입력/응답 표시                                             │  │
│  │  - 전처리/의도분류/스킬 매칭 결과 패널 (Portal 역할)               │  │
│  │  - Direct Routing 모드 전환 (SA 선택 UI 없음)                      │  │
│  └───────────────┬─────────────────────────────────────────────────────┘  │
│                  │ (사용자 입력 + 세션키)                                 │
│                  ▼                                                       │
│        ┌──────────────────────┐        ┌──────────────────────┐          │
│        │ Master Agent (MA)    │        │   Skill Set (SK)     │          │
│        │  - Guardrail         │        │  - 스킬 탐색         │          │
│        │    (전처리/금칙어/PII)│        └──────────┬───────────┘          │
│        │  - 의도분류          │                   │                      │
│        │  - 스킬 매칭         │                   │ (스킬매칭 결과)      │
│        │  - SA Mock 호출      │                   ▼                      │
│        └──────────┬───────────┘           ┌───────────────┐              │
│                   │                       │   Demo UI      │ (모니터링)  │
│                   │ (세션/컨텍스트/프로파일 조회·저장)     └───────────────┘  │
│                   ▼                                                       │
│     ┌────────────────────────────────────────────────────────────────┐    │
│     │                        Session Manager (SM)                    │    │
│     │  - MA 요청 시 Global Session Key 자동 생성 및 저장           │    │
│     │  - 세션 생성/조회/업데이트/종료 (MA 요청)                     │    │
│     │  - 대화 이력 저장/조회 (MA 요청)                              │    │
│     │  - 고객 프로파일 스냅샷 저장/조회 (세션 API 내 customer_profile)│   │
│     │  - 상태 저장소: Redis (세션/컨텍스트/매핑)                     │    │
│     │    - session:{global_session_key}, context:{context_id},       │    │
│     │      session_map:{global_session_key}:{agent_id}               │    │
│     │  📌 Local Session Key는 Sprint 3+에서 구현                      │    │
│     └────────────────────────────────────────────────────────────────┘    │
│                   ▲                                                       │
│                   │ (최종 응답 - MA → Demo UI)                            │
│                   │                                                       │
│        ┌──────────┴───────────┐                                           │
│        │   SA Mock API        │                                           │
│        │   (Exchange 등)      │                                           │
│        │ GET /sa-mock/...     │                                           │
│        └──────────────────────┘                                           │
└────────────────────────────────────────────────────────────────────────────┘
```

**향후 Sprint**: Client와 Portal이 별도 시스템으로 분리

---

## � 세션 생성 프로세스 (중요!)

### 역할 분리

| 컴포넌트 | 역할 | 생성하는 것 |
|---------|------|-----------|
| **Client (Demo UI)** | 세션 생성 요청 | 요청만 보냄 (user_id, channel 등) |
| **Session Manager** | 세션 키 및 객체 생성 | `gsess_{timestamp}_{uuid}`, Session 데이터 (conversation_id, context_id, state, expires_at, customer_profile 등) |
| **MA** | 중계 + 전처리/의도분류 | SM 세션 API 호출 (`/agw/sessions`, `/ma/sessions/resolve` 등) |

### 세션 키 vs 세션 객체

```javascript
// ❌ Client가 하지 않는 것: 세션 키나 객체 생성
// Client는 세션 요청만 보냄니다!

// ✅ Client가 하는 것: 세션 생성 요청
// 단순히 user_id, channel 등 요청 데이터만 보냄

// ✅ Session Manager가 하는 것: 세션 키 및 객체 생성
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",  // SM이 생성
  "conversation_id": "conv_20260101_001",  // SM이 생성
  "context_id": "ctx_20260101_001",        // SM이 생성
  "session_state": "start",                 // SM이 초기화
  "expires_at": "2026-01-01T11:00:00Z",    // SM이 계산
  "created_at": "2026-01-01T10:00:00Z",    // SM이 기록
  // ... 기타 세션 관리 데이터
}
```

### 왜 이렇게 분리했나?

1. **Client 부담 감소**: 복잡한 세션 관리 로직 불필요
2. **일관성 보장**: SM이 중앙에서 세션 생성 규칙 관리
3. **확장성**: Client는 단순 요청만, SM은 복잡한 세션 로직 처리
4. **추적성**: SM이 생성한 키로 전체 흐름 추적 가능

---

### 📝 시나리오 1: Happy Case (스킬 탐색 후 SA 실행)

### Step 1: 첫 메시지 입력 및 세션 생성 (Client → AGW → SM, Demo UI → MA → SM 관점)

**Trigger**: 사용자가 Client 채팅 영역에서 첫 메시지 입력

**1-1. Client/Demo UI**: 세션 생성 요청 준비
```javascript
// Client는 세션 키를 생성하지 않고 요청 데이터만 준비
// Session Manager가 global_session_key를 자동으로 생성하여 반환함
```

**1-2. Demo UI → MA**: 첫 메시지 전송 (상용에서는 Client → AGW → MA 체인으로 확장 예정)
```json
{
  "user_id": "user_vip_001",
  "channel": "web",
  "message": "환율 1400원 이상일 때 100만원 환전해줘"
}
```

**1-3. MA → Session Manager**: 세션 생성 요청 (실제 세션 키 및 객체 생성, 개인화 프로파일 포함)
```http
POST http://localhost:8080/api/v1/agw/sessions
X-API-Key: agw-api-key   # Demo에서는 MA(Guardrail 포함)가 호출

{
  "user_id": "user_vip_001",                             // 필수
  "channel": "web",                                       // 필수
  "device_info": {"type": "web", "browser": "Chrome"},   // 옵션 (데모용)
  "customer_profile": {                                      // 옵션 - 개인화 프로파일 스냅샷
    "user_id": "user_vip_001",
    "segment": "VIP",
    "attributes": [
      {"key": "tier", "value": "platinum", "source_system": "CRM"},
      {"key": "preferred_language", "value": "ko", "source_system": "CRM"}
    ],
    "preferences": {"language": "ko"}
  }
  // "request_id": "req_001"  // 옵션 (추적용, 데모에서는 생략)
}
```

**📌 중요**: 이 시점에서 Session Manager가 실제 세션 객체를 생성합니다!

**1-4. Session Manager 내부 처리**
```python
# Session Manager가 수행하는 작업:
# 1. MA 요청 수신
# 2. global_session_key 자동 생성
# 3. 새로운 세션 객체 생성
session = {
    "global_session_key": generate_id("gsess"),  # SM이 생성
    "conversation_id": generate_id("conv"),  # SM이 생성
    "context_id": generate_id("ctx"),        # SM이 생성
    "session_state": "start",                 # SM이 초기화
    "user_id": "user_vip_001",
    "channel": "web",
    "expires_at": now() + 1hour,             # SM이 계산
    "created_at": now(),                      # SM이 기록
    # ... 기타 세션 관리 데이터
}
# 4. 세션을 데이터베이스/메모리에 저장
save_session(session)
```

**1-5. Session Manager → AGW**: 세션 생성 응답
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",  // SM이 생성한 키
  "conversation_id": "conv_20260101_001",  // SM이 생성한 대화 ID
  "context_id": "ctx_20260101_001",        // SM이 생성한 컨텍스트 ID
  "session_state": "start",                 // SM이 관리하는 상태
  "expires_at": "2026-01-01T11:00:00Z",    // SM이 계산한 만료시간
  "is_new": true                            // SM이 판단한 신규 여부
}
```

**1-6. AGW**: 세션 정보 저장 및 전처리 시작
- SM에서 받은 conversation_id, context_id를 메모리에 저장
- 사용자 메시지 전처리 시작

**1-5. AGW 전처리** (동의어, 금칙어, PII 처리):
```python
# 1. 금칙어 필터링
filtered_words = []  # 금칙어 없음

# 2. 동의어 치환
# "환전해줘" → "환전하다"
synonyms_applied = ["환전하다"]

# 3. PII 처리
pii_detected = []  # 개인정보 없음

# 4. 정규화
preprocessed = "환율 1400원 이상일 때 100만원 환전해줘"
```

**1-6. AGW → Portal** (전처리 결과 - 모니터링용):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "preprocessing_result": {
    "original": "환율 1400원 이상일 때 100만원 환전해줘",
    "preprocessed": "환율 1400원 이상일 때 100만원 환전해줘",
    "filtered_words": [],
    "synonyms_applied": ["환전하다"],
    "pii_detected": []
  }
}
```

> **Sprint 2**: MA 요청 시 Session Manager가 Global Session Key 자동 생성 → 저장  
> **Sprint 3+**: Local Session Key 도입 (업무 Agent별 세션 매핑)

---

### Step 2: 의도분류 및 세션 조회 (MA → SM)

**2-1. MA 내부** (전처리된 메시지 + 세션 키 처리):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "message": "환율 1400원 이상일 때 100만원 환전해줘",
  "preprocessing_metadata": {
    "synonyms_applied": ["환전하다"],
    "filtered_words": [],
    "pii_detected": []
  }
}
```

**2-2. MA → Session Manager**: 세션 조회 (고객 프로파일 포함)
```http
GET http://localhost:8080/api/v1/ma/sessions/resolve?global_session_key=gsess_1735689600000_a1b2c3d4&channel=web
X-API-Key: ma-api-key

// Query Parameters:
// - global_session_key: 필수
// - channel: 옵션 (데모에서는 포함)
// - agent_type: 옵션 (Sprint 2에서는 미사용)
// - agent_id: 옵션 (Sprint 2에서는 미사용)
```

**2-3. Session Manager → MA**: 세션 정보 응답
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "conversation_id": "conv_20260101_001",
  "context_id": "ctx_20260101_001",
  "session_state": "start",
  "is_first_call": true,
  "task_queue_status": "null",
  "subagent_status": "undefined",
  "customer_profile": {
    "user_id": "user_vip_001",
    "segment": "VIP",
    "attributes": [
      {"key": "tier", "value": "platinum", "source_system": "CRM"},
      {"key": "preferred_language", "value": "ko", "source_system": "CRM"}
    ],
    "preferences": {"language": "ko"}
  }
}
```

> ℹ️ **Demo 기본 흐름에서는** 위 `customer_profile`을 사용하여 개인화 정보를 활용합니다.
> 최신 정보를 강제로 조회해야 하는 경우에만 아래 프로파일 API를 추가로 호출합니다.

**2-4. (선택) MA → Session Manager**: 프로파일 조회
```http
GET http://localhost:8080/api/v1/ma/profiles/user_vip_001
X-API-Key: ma-api-key
```

**2-5. Session Manager → MA**: 프로파일 응답
```json
{
  "user_id": "user_vip_001",
  "profile": {
    "user_id": "user_vip_001",
    "segment": "VIP",
    "attributes": [
      {"key": "tier", "value": "platinum", "source_system": "CRM"},
      {"key": "preferred_language", "value": "ko", "source_system": "CRM"}
    ]
  }
}
```

**2-6. MA 내부 처리**: 의도 분류
```python
# NLU 모델로 의도 분류
intent = classify_intent("환율 1400원 이상일 때 100만원 환전해줘")
# → "exchange_currency_conditional"

confidence = 0.95
entities = {
  "exchange_rate_condition": "1400원 이상",
  "amount_krw": 1000000
}
```

**2-7. MA → Portal** (의도 분류 결과 - 모니터링용):
```json
{
  "global_session_key": "gsess_20260101_uuid_001",
  "intent_classification": {
    "intent": "exchange_currency_conditional",
    "confidence": 0.95,
    "entities": {
      "exchange_rate_condition": "1400원 이상",
      "amount_krw": 1000000
    }
  }
}
```

**Portal 화면** (결과 표시):
```
┌─────────────────────────────────────────┐
│ [의도 분류 결과]                         │
│ 🎯 의도: 조건부 환전                    │
│ 📊 신뢰도: 95%                          │
│ 📌 엔티티:                              │
│   - 환율 조건: 1400원 이상              │
│   - 금액: 100만원                       │
└─────────────────────────────────────────┘
```

---

### Step 3: 스킬 탐색 (MA → SK → Portal)

**3-1. MA → Skill Set (SK)**: 스킬 탐색 요청
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "intent": "exchange_currency_conditional",
  "entities": {
    "exchange_rate_condition": "1400원 이상",
    "amount_krw": 1000000
  },
  "user_profile": {
    "segment": "VIP",
    "tier": "platinum"
  }
}
```

**3-2. SK (Skill Set) 처리**:
```python
# 스킬 데이터베이스 조회
skill = search_skill_by_intent("exchange_currency_conditional")
# → {
#     "skill_id": "sk_exchange_001",
#     "agent_id": "sa_exchange",
#     "agent_name": "환전 업무 에이전트",
#     "agent_type": "업무",
#     "confidence": 0.95
#   }
```

**SK → MA** (스킬 탐색 결과):
```json
{
  "skill_id": "sk_exchange_001",
  "agent_id": "sa_exchange",
  "agent_name": "환전 업무 에이전트",
  "agent_type": "업무",
  "confidence": 0.95
}
```

**SK → Portal** (스킬 탐색 결과 - 표시용):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "skill_matching_result": {
    "skill_id": "sk_exchange_001",
    "agent_id": "sa_exchange",
    "agent_name": "환전 업무 에이전트",
    "agent_type": "업무",
    "confidence": 0.95
  }
}
```

**Portal 화면** (스킬 매칭 결과):
```
┌─────────────────────────────────────────┐
│ [스킬 매칭 결과]                         │
│ 🤖 매칭된 에이전트: 환전 업무 에이전트   │
│ 🆔 Agent ID: sa_exchange                │
│ 📊 신뢰도: 95%                          │
│                                         │
│ [업무 에이전트 실행]  [다시 검색]       │
└─────────────────────────────────────────┘
```

> **주의**: MA는 스킬 탐색 후 **SA에 바로 보내지 않고** Client의 선택을 기다립니다.

---

### Step 4: 대화 턴 저장 (MA → SM)

**4-1. MA → Session Manager**: 대화 턴 저장
```http
POST http://localhost:8080/api/v1/ma/context/turn
X-API-Key: ma-api-key

{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "context_id": "ctx_20260101_001",
  "turn": {
    "turn_id": "turn_001",
    "role": "user",
    "content": "환율 1400원 이상일 때 100만원 환전해줘",
    "timestamp": "2026-01-01T10:01:00Z"
  }
}
```

**4-2. Session Manager → MA**: 응답
```json
{
  "turn_id": "turn_001",
  "saved_at": "2026-01-01T10:01:00Z",
  "status": "success"
}
```

---

### Step 5: 스킬 매칭 완료 알림 (MA → Client)

**5-1. MA → Client** (처리 완료 - 채팅 영역):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "status": "skill_matched",
  "message": "스킬 탐색이 완료되었습니다. 업무 에이전트를 실행하시겠습니까?",
  "matched_agent": {
    "agent_id": "sa_exchange",
    "agent_name": "환전 업무 에이전트",
    "status": "ready"
  }
}
```

**Client 화면** (채팅 영역):
```
┌─────────────────────────────────────────┐
│ 🤖 환전 업무 에이전트가 준비되었습니다.  │
│                                         │
│ [업무 에이전트 실행 (Continue)]          │
│ [메시지 추가 입력]                       │
│ [취소 (Fallback)]                       │
└─────────────────────────────────────────┘
```

---

### Step 9: Client에서 SA 실행 선택

**사용자 액션**: Client 채팅 영역에서 "업무 에이전트 실행 (Continue)" 버튼 클릭

---

### Step 6: Client의 Continue 선택 (Client → MA)

**6-1. Client → MA** (빈 메시지 + Continue):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "user_input": "",
  "subagent_action": "continue",
  "selected_agent": "sa_exchange"
}
```

---

### Step 7: 세션 상태 업데이트 (MA → SM)

**7-1. MA → Session Manager**: 세션 상태 업데이트
```http
PATCH http://localhost:8080/api/v1/ma/sessions/state
X-API-Key: ma-api-key

{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",  // 필수
  "conversation_id": "conv_20260101_001",                 // 필수
  "turn_id": "turn_001",                                  // 필수
  "session_state": "talk",                                // 필수 (start/talk/end)
  "state_patch": {                                        // 필수 객체 (내부 필드는 모두 옵션)
    "subagent_status": "continue",                        // 옵션
    "last_agent_id": "sa_exchange",                       // 옵션
    "last_agent_type": "task"                             // 옵션
    // "action_owner": "ma"                               // 옵션 (데모에서 미사용)
    // "reference_information": {}                        // 옵션 (데모에서 미사용)
    // "cushion_message": ""                              // 옵션 (데모에서 미사용)
    // "last_response_type": "continue"                   // 옵션 (데모에서 미사용)
  }
}
```

**7-2. Session Manager → MA**: 응답
```json
{
  "status": "success",
  "updated_at": "2026-01-01T10:02:00Z"
}
```

---

### Step 8: SA Mock API 호출 (MA → SA Mock API → MA → Client)

> **Sprint 2 제약**: Sub Agent가 없으므로 **별도 Mock API**로 구현

**8-1. MA → SA Mock API** (GET 요청):
```http
GET /sa-mock/exchange?session_key=gsess_1735689600000_a1b2c3d4&amount=1000000&rate_condition=1400
```

**8-2. SA Mock API → MA**: 응답
```json
{
  "agent_id": "sa_exchange",
  "status": "end",
  "response_code": "SUCCESS",
  "message": "100만원을 환전하였습니다.",
  "metadata": {
    "transaction_id": "TXN_20260101_001",
    "exchange_rate": 1450.0,
    "amount_usd": 689.66,
    "execution_time_ms": 350
  }
}
```

**8-3. MA → Client** (최종 응답 - 채팅 영역):
```json
{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "agent_id": "sa_exchange",
  "status": "end",
  "message": "100만원을 환전하였습니다.",
  "metadata": {
    "transaction_id": "TXN_20260101_001",
    "exchange_rate": 1450.0,
    "amount_usd": 689.66
  }
}
```

**Client 화면** (채팅 영역):
```
┌─────────────────────────────────────────┐
│ 🤖 환전 업무 에이전트                    │
│                                         │
│ 100만원을 환전하였습니다.                │
│                                         │
│ 📋 거래 상세:                           │
│   - 거래 ID: TXN_20260101_001          │
│   - 환율: 1,450.0원/$                  │
│   - 달러 금액: $689.66                 │
│   - 실행 시간: 350ms                   │
│                                         │
│ ✅ 대화가 종료되었습니다.                │
└─────────────────────────────────────────┘
```

---

### Step 9: 대화 종료 및 저장 (MA → SM → Client)

**9-1. MA → Session Manager**: 최종 응답 턴 저장
```http
POST http://localhost:8080/api/v1/ma/context/turn
X-API-Key: ma-api-key

{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",
  "context_id": "ctx_20260101_001",
  "turn": {
    "turn_id": "turn_002",
    "role": "assistant",
    "content": "100만원을 환전하였습니다.",
    "timestamp": "2026-01-01T10:02:30Z"
  }
}
```

**9-2. MA → Session Manager**: 세션 종료
```http
POST http://localhost:8080/api/v1/ma/sessions/close
X-API-Key: ma-api-key

{
  "global_session_key": "gsess_1735689600000_a1b2c3d4",  // 필수
  "conversation_id": "conv_20260101_001",                 // 필수
  "close_reason": "task_completed",                       // 필수
  "final_summary": "환율 조건부 환전 완료"               // 옵션 (데모에서는 포함)
}
```

**9-3. Session Manager → MA**: 종료 확인
```json
{
  "status": "success"
}
```

**시연 완료!** ✅

---

## 📝 시나리오 2: Direct Routing (직접 에이전트 선택)

### Step 1: Direct Routing 활성화

**Client 첫 화면** (채팅 영역):
```
┌─────────────────────────────────────────┐
│ Session Manager Demo                   │
│                                         │
│ [일반 대화 시작]                         │
│ [Direct Routing] ← 클릭                 │
└─────────────────────────────────────────┘
```

---

### Step 2: 업무 에이전트 선택

**Direct Routing 팝업**:
```
┌─────────────────────────────────────────┐
│ 업무 에이전트 선택                       │
├─────────────────────────────────────────┤
│ ○ 환전 업무 에이전트 (sa_exchange)       │
│ ○ 송금 업무 에이전트 (sa_transfer)       │
│ ○ 예금 업무 에이전트 (sa_deposit)        │
│                                         │
│          [선택]       [취소]            │
└─────────────────────────────────────────┘
```

**사용자 선택**: "환전 업무 에이전트" 선택

---

### Step 3: 메시지 입력 및 전송

**Client UI** (채팅 영역):
```
┌─────────────────────────────────────────┐
│ 🤖 환전 업무 에이전트 (Direct)           │
│                                         │
│ 100만원 환전해줘                        │  [전송]
└─────────────────────────────────────────┘
```

**Client → MA** (Direct Routing 요청):
```json
{
  "routing_type": "direct",
  "agent_id": "sa_exchange",
  "user_input": "100만원 환전해줘",
  "global_session_key": "gsess_1735689700000_b2c3d4e5"
}
```

> **주의**: Direct Routing에서는 AGW 전처리, MA 의도분류, SK 스킬탐색을 **건너뛰고** MA가 바로 SA Mock API를 호출합니다.

---

### Step 4: SA Mock API 호출 및 응답 (MA → SA Mock API → MA → Client)

**MA → SA Mock API** (GET 요청):
```http
GET /sa-mock/exchange?session_key=gsess_1735689700000_b2c3d4e5&amount=1000000
```

**SA Mock API 응답**:
```json
{
  "agent_id": "sa_exchange",
  "status": "end",
  "response_code": "SUCCESS",
  "message": "100만원을 환전하였습니다.",
  "metadata": {
    "transaction_id": "TXN_20260101_002",
    "exchange_rate": 1450.0,
    "amount_usd": 689.66
  }
}
```

**MA → Client** (최종 응답 - 채팅 영역):
```json
{
  "global_session_key": "gsess_1735689700000_b2c3d4e5",
  "agent_id": "sa_exchange",
  "status": "end",
  "message": "100만원을 환전하였습니다.",
  "metadata": {
    "transaction_id": "TXN_20260101_002",
    "exchange_rate": 1450.0,
    "amount_usd": 689.66
  }
}
```

**Client 화면** (채팅 영역):
```
┌─────────────────────────────────────────┐
│ 🤖 환전 업무 에이전트 (Direct)           │
│                                         │
│ 100만원을 환전하였습니다.                │
│                                         │
│ 📋 거래 ID: TXN_20260101_002           │
│ 💵 환율: 1,450.0원/$                   │
│ 💰 달러 금액: $689.66                  │
│                                         │
│ ✅ 처리 완료                            │
└─────────────────────────────────────────┘
```

---

### Direct Routing vs Happy Case 비교

| 구분 | Happy Case | Direct Routing |
|------|------------|----------------|
| **전처리** | ✅ AGW 전처리 | ❌ 건너뜀 |
| **의도분류** | ✅ MA 의도분류 | ❌ 건너뜀 |
| **스킬탐색** | ✅ SK 스킬탐색 | ❌ 건너뜀 |
| **SA 선택** | 자동 (SK 결과) | 수동 (사용자 선택) |
| **응답 경로** | Client → AGW → MA → SA Mock API → MA → Client | Client → MA → SA Mock API → MA → Client |
| **응답속도** | 느림 (3단계 처리) | 빠름 (전처리 건너뜀) |
| **사용 사례** | 일반 대화 | 명확한 업무 지시 |

---

## 🎯 Session Manager API 요약

**Session Manager가 제공하는 API만**:

| API | 호출자 | 용도 |
|-----|--------|------|
| `POST /agw/sessions` | AGW | 세션 생성 (글로벌 키 발급) |
| `POST /ma/sessions/resolve` | MA | 세션 조회 |
| `POST /ma/sessions/{key}/turn` | MA | 대화 턴 저장 |
| `PATCH /ma/sessions/{key}/status` | MA | 세션 상태 업데이트 |
| `GET /ma/sessions/{key}/history` | MA | 대화 이력 조회 |
| `GET /ma/profiles/{user_id}` | MA | 프로파일 조회 |
| `POST /batch/profiles` | VDB | 프로파일 배치 |

**Session Manager 역할**: 세션/컨텍스트/프로파일 관리만  
**Client, Portal, SK, SA Mock API는 별도 시스템** (SM이 관여하지 않음)

---

## 📝 시연 체크리스트

### Session Manager (백엔드)
- [ ] Session Manager 서버 실행 (`uv run uvicorn app.main:app --port 8080`)
- [ ] Mock 데이터 준비 (user_vip_001 프로파일)
- [ ] API Key 확인 (`.env` 파일)
- [ ] Postman/Curl로 API 호출 테스트

### Demo Front-end

**Client 영역** (채팅):
- [ ] 대화 입력 UI
- [ ] SA/Direct Routing 선택 UI
- [ ] 메시지 전송 버튼
- [ ] 최종 응답 표시 (채팅)
- [ ] Direct Routing 팝업

**Portal 영역** (결과 표시):
- [ ] 전처리 결과 표시 화면
- [ ] 의도 분류 결과 표시 화면
- [ ] 스킬 매칭 결과 표시 화면
- [ ] 스킬셋 설정 UI

### Mock 시스템
- [ ] AGW Mock (전처리 모듈)
- [ ] MA Mock (의도분류)
- [ ] SK Mock (스킬 탐색)
- [ ] **SA Mock API** (별도 구현 필요)
  - [ ] `GET /sa-mock/exchange` 엔드포인트
  - [ ] 환전 로직 Mock
  - [ ] JSON 응답 반환

---

## 🎯 시연 성공 기준

### Happy Case
✅ Client가 세션 생성 요청 (Global Session Key는 Session Manager가 생성)  
✅ 세션 생성 성공 (Session Manager가 키 및 세션 객체 생성/저장)  
✅ Client 채팅 영역에서 메시지 입력  
✅ 전처리 결과 Portal에 표시  
✅ 의도 분류 결과 Portal에 표시  
✅ 스킬 매칭 결과 Portal에 표시  
✅ Client 채팅 영역에서 "업무 에이전트 실행" 선택  
✅ **MA → SA Mock API → MA → Client** 응답 경로 확인  
✅ Client 채팅 영역에 "100만원을 환전하였습니다." 표시  
✅ 대화 이력 Session Manager에 저장

### Direct Routing
✅ Client가 세션 생성 요청 (Global Session Key는 Session Manager가 생성)  
✅ Direct Routing 팝업 정상 동작 (Client)  
✅ 업무 에이전트 직접 선택 가능  
✅ Client → MA → SA Mock API → MA → Client 경로 확인  
✅ Client 채팅 영역에 응답 표시

### Sprint 2 제약사항 확인
✅ **Global Session Key만 사용** (Local Key 없음)  
✅ Session Manager가 Global Session Key 및 세션 객체 생성/관리  
📌 Local Session Key는 Sprint 3+에서 구현

---

**Sprint 2 시연 준비 완료!** 🎉
