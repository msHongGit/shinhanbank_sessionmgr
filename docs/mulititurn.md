# 멀티턴 세션 컨텍스트 명세서

> **버전**: 1.0  
> **작성일**: 2026-01-11  
> **작성팀**: Master Agent 팀  
> **상태**: 구현 필요

---

## 1. 개요

이 문서는 **Agent Gateway**, **Session Manager**, **Master Agent** 간 멀티턴 대화 처리를 위한 세션 컨텍스트 필드 명세입니다.

### 1.1 현재 문제점

멀티턴 대화가 정상 작동하지 않는 이유:
1. Master Agent가 PATCH를 통해 Session Manager에 컨텍스트 저장
2. Session Manager가 GET 응답에서 해당 필드를 반환하지 않음
3. Agent Gateway가 해당 필드를 Master Agent에 전달하지 않음
4. Turn 2 이후 컨텍스트가 유실되어 일반적인 응답으로 fallback

### 1.2 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TURN 1 (최초 요청)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   사용자 ──► Agent Gateway ──► Session Manager (GET) ──► Agent Gateway      │
│                                      │                       │              │
│                            (컨텍스트 없음)           (session_context 생성)  │
│                                                              │              │
│                                                              ▼              │
│                                                        Master Agent         │
│                                                              │              │
│                                      ┌───────────────────────┘              │
│                                      ▼                                      │
│                             Session Manager (PATCH)                         │
│                                      │                                      │
│                     ┌────────────────┴────────────────┐                     │
│                     │  reference_information:         │                     │
│                     │    - active_task                │                     │
│                     │    - conversation_history       │                     │
│                     │    - current_intent             │                     │
│                     └─────────────────────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        TURN 2 (연속 요청)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   사용자 ──► Agent Gateway ──► Session Manager (GET) ──► Agent Gateway      │
│                                      │                       │              │
│                     ┌────────────────┴────────────────┐      │              │
│                     │  ✅ 반드시 반환 필요:            │      │              │
│                     │    - active_task                │      │              │
│                     │    - conversation_history       │      │              │
│                     │    - current_intent             │      │              │
│                     └─────────────────────────────────┘      │              │
│                                                              │              │
│                                              ✅ 반드시 전달  ▼              │
│                                                        Master Agent         │
│                                                              │              │
│                                               (DirectRouting 발동)          │
│                                                              │              │
│                                                              ▼              │
│                                                     대화 계속 진행           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Session Manager 요구사항

### 2.1 PATCH 요청: `reference_information` 필드 수용

Master Agent가 `state_patch.reference_information`을 통해 컨텍스트를 전송합니다. Session Manager는 모든 필드를 수용하고 저장해야 합니다.

#### PATCH 엔드포인트
```
PATCH /api/v1/sessions/{global_session_key}/state
```

#### 요청 페이로드 스키마

```json
{
  "global_session_key": "string (필수)",
  "turn_id": "string (필수)",
  "session_state": "start | talk | end",
  "state_patch": {
    "subagent_status": "undefined | continue | end",
    "action_owner": "string",
    "cushion_message": "string | null",
    "last_agent_id": "string",
    "last_agent_type": "knowledge | skill",
    "last_response_type": "continue | end",
    "agent_session_key": "string | null",
    "session_attributes": {},
    
    "reference_information": {
      "active_task": {
        "task_id": "string",
        "intent": "string",
        "skill_tag": "string",
        "skillset_metadata": {
          "agent": "string",
          "skill": "string",
          "sub_skill": "string | null"
        }
      },
      "conversation_history": [
        {
          "role": "user | assistant",
          "content": "string"
        }
      ],
      "current_intent": "string | null",
      "current_task_id": "string | null",
      "task_queue_status": [
        {
          "task_id": "string",
          "intent": "string",
          "status": "Pending | Running | Completed | Failed",
          "skill_tag": "string"
        }
      ],
      "turn_count": "integer"
    }
  }
}
```

#### `reference_information` 필드 정의

| 필드명 | 타입 | 필수 여부 | 설명 |
|--------|------|----------|------|
| `active_task` | object \| null | 아니오 | 사용자 입력 대기 중인 활성 태스크 (DirectRouting용) |
| `active_task.task_id` | string | 예* | 고유 태스크 식별자 |
| `active_task.intent` | string | 예* | 사용자 의도 (예: "계좌조회") |
| `active_task.skill_tag` | string | 예* | 라우팅용 스킬 태그 (예: "balance_inquiry") |
| `active_task.skillset_metadata` | object \| null | 아니오 | 스킬셋 에이전트의 추가 메타데이터 |
| `conversation_history` | array | 아니오 | 최근 N개 대화 턴 (최대 10개) |
| `conversation_history[].role` | string | 예* | "user" 또는 "assistant" |
| `conversation_history[].content` | string | 예* | 메시지 내용 |
| `current_intent` | string \| null | 아니오 | 현재 활성 의도 |
| `current_task_id` | string \| null | 아니오 | 현재 태스크 ID (상관관계 추적용) |
| `task_queue_status` | array | 아니오 | 대기/진행 중인 태스크 목록 |
| `turn_count` | integer | 아니오 | 대화 턴 수 |

*상위 객체가 존재할 경우 필수

---

### 2.2 GET 응답: 멀티턴 컨텍스트 반환

Agent Gateway가 세션을 조회할 때, Session Manager는 저장된 `reference_information` 필드를 반환해야 합니다.

#### GET 엔드포인트
```
GET /api/v1/sessions/{global_session_key}
```

#### 응답 페이로드 스키마

**옵션 A: 최상위 레벨로 펼침 (권장)**

```json
{
  "global_session_key": "gsess_xxx",
  "agent_session_key": "agent_sess_xxx",
  "user_id": "user_001",
  "session_state": "talk",
  "is_first_call": false,
  
  "channel": {
    "eventType": "natural_language",
    "eventChannel": "utterance"
  },
  
  "task_queue_status": "notnull",
  "subagent_status": "continue",
  
  "last_event": {
    "event_type": "agent_response",
    "agent_id": "master-agent",
    "agent_type": "knowledge",
    "response_type": "continue",
    "updated_at": "2026-01-11T03:00:00.000Z"
  },
  
  "customer_profile": {
    "user_id": "user_001",
    "attributes": [],
    "segment": "general",
    "preferences": {}
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

**옵션 B: `reference_information` 내부에 중첩 유지**

```json
{
  "global_session_key": "gsess_xxx",
  "session_state": "talk",
  "subagent_status": "continue",
  
  "reference_information": {
    "active_task": {...},
    "conversation_history": [...],
    "current_intent": "계좌조회",
    "current_task_id": "task-001",
    "task_queue_status": [...],
    "turn_count": 1
  }
}
```

> **참고**: 옵션 B를 선택할 경우, Agent Gateway가 `reference_information`에서 필드를 추출하여 Master Agent에 전달해야 합니다.

---

## 3. Agent Gateway 요구사항

### 3.1 Session Manager 응답에서 `session_context` 구성

Agent Gateway는 Session Manager GET 응답을 Master Agent 호출 시 `session_context`로 매핑해야 합니다.

#### 매핑 로직 (의사코드)

```python
def build_session_context(sm_response: dict) -> dict:
    """Session Manager 응답을 Master Agent session_context로 매핑."""
    
    # reference_information 추출 (펼침/중첩 모두 처리)
    ref_info = sm_response.get("reference_information", {})
    
    return {
        # 세션 식별 정보
        "global_session_key": sm_response["global_session_key"],
        "user_id": sm_response.get("customer_profile", {}).get("user_id"),
        "session_state": sm_response.get("session_state", "talk"),
        "is_first_call": sm_response.get("is_first_call", False),
        
        # 채널 정보
        "channel": sm_response.get("channel", {}),
        
        # 상태 필드
        "task_queue_status": sm_response.get("task_queue_status", "null"),
        "subagent_status": sm_response.get("subagent_status", "undefined"),
        "last_event": sm_response.get("last_event"),
        
        # 고객 프로필
        "customer_profile": sm_response.get("customer_profile", {}),
        
        # ========================================
        # 중요: 멀티턴 컨텍스트 필드
        # ========================================
        
        # 옵션 A: 펼쳐진 필드
        "active_task": sm_response.get("active_task") or ref_info.get("active_task"),
        
        "conversation_history": (
            sm_response.get("conversation_history") or 
            ref_info.get("conversation_history")
        ),
        
        "current_intent": (
            sm_response.get("current_intent") or 
            ref_info.get("current_intent")
        ),
        
        # 참고: task_queue_status_detail vs task_queue_status 네이밍
        "task_queue_status_detail": (
            sm_response.get("task_queue_status_detail") or 
            ref_info.get("task_queue_status")
        ),
    }
```

### 3.2 Master Agent 호출 요청

Agent Gateway가 Master Agent에 전송하는 요청:

```
POST /api/v1/agent/invoke
```

#### 요청 페이로드

```json
{
  "gateway_context": {
    "pre_processing": {
      "guardrail_passed": true
    }
  },
  
  "session_context": {
    "global_session_key": "gsess_xxx",
    "user_id": "user_001",
    "session_state": "talk",
    "is_first_call": false,
    
    "channel": {
      "eventType": "natural_language",
      "eventChannel": "utterance"
    },
    
    "task_queue_status": "notnull",
    "subagent_status": "continue",
    
    "customer_profile": {
      "user_id": "user_001"
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
    
    "current_intent": "계좌조회"
  },
  
  "user_request": {
    "user_query": "110-123-456789",
    "channel": {
      "event_channel": "utterance",
      "event_type": "natural_language"
    }
  },
  
  "turn_id": "turn_002_xxx"
}
```

---

## 4. 필드 참조 요약

### 4.1 멀티턴 컨텍스트 필드

| 필드명 | 출처 | 목적지 | 용도 |
|--------|------|--------|------|
| `active_task` | Master Agent → SM | SM → GW → MA | DirectRouting: 의도 추론 건너뛰고 활성 태스크로 계속 진행 |
| `conversation_history` | Master Agent → SM | SM → GW → MA | LLM 컨텍스트: 대화 맥락 제공 |
| `current_intent` | Master Agent → SM | SM → GW → MA | 의도 보존: 현재 사용자 의도 추적 |
| `task_queue_status` (detail) | Master Agent → SM | SM → GW → MA | 태스크 추적: 대기/진행 중 태스크 목록 |
| `turn_count` | Master Agent → SM | SM → GW → MA | 턴 추적: 대화 턴 횟수 |

### 4.2 상태 필드 값

| 필드명 | 유효값 | 설명 |
|--------|--------|------|
| `session_state` | `start`, `talk`, `end` | 세션 생명주기 상태 |
| `subagent_status` | `undefined`, `continue`, `end` | 서브에이전트 대화 상태 |
| `task_queue_status` | `null`, `notnull` | 대기 중인 태스크 존재 여부 |
| `last_response_type` | `continue`, `end` | 마지막 에이전트 응답 유형 |
| `last_agent_type` | `knowledge`, `skill` | 마지막 응답 에이전트 유형 |

---

## 5. 예시: 잔액조회 멀티턴 흐름

### Turn 1: 사용자가 잔액 조회 요청

**사용자 입력**: "계좌 잔액 조회해주세요"

**Master Agent 응답**: "계좌번호를 알려주세요."

**Master Agent → Session Manager PATCH**:
```json
{
  "global_session_key": "gsess_001",
  "turn_id": "turn_001",
  "session_state": "talk",
  "state_patch": {
    "subagent_status": "continue",
    "last_agent_type": "skill",
    "last_response_type": "continue",
    "reference_information": {
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
      "turn_count": 1
    }
  }
}
```

### Turn 2: 사용자가 계좌번호 제공

**Session Manager GET 응답** (Agent Gateway로):
```json
{
  "global_session_key": "gsess_001",
  "session_state": "talk",
  "subagent_status": "continue",
  "active_task": {
    "task_id": "task-001",
    "intent": "계좌조회",
    "skill_tag": "balance_inquiry"
  },
  "conversation_history": [
    {"role": "user", "content": "계좌 잔액 조회해주세요"},
    {"role": "assistant", "content": "계좌번호를 알려주세요."}
  ],
  "current_intent": "계좌조회"
}
```

**Agent Gateway → Master Agent** (session_context):
```json
{
  "session_context": {
    "global_session_key": "gsess_001",
    "subagent_status": "continue",
    "active_task": {
      "task_id": "task-001",
      "intent": "계좌조회",
      "skill_tag": "balance_inquiry"
    },
    "conversation_history": [...],
    "current_intent": "계좌조회"
  },
  "user_request": {
    "user_query": "110-123-456789"
  }
}
```

**Master Agent 동작**:
1. 페이로드에서 `active_task` 감지 → **DirectRouting** 발동
2. 의도 추론 (NeedInference) 건너뜀
3. 잔액조회 스킬로 대화 계속 진행
4. 잔액 결과 반환

---

## 6. 구현 체크리스트

### Session Manager 팀

- [ ] PATCH 요청에서 `reference_information` 필드 수용
- [ ] `active_task`, `conversation_history`, `current_intent` 등 저장
- [ ] GET 응답에서 해당 필드 반환 (펼침 또는 중첩)
- [ ] 신규 필드에 대한 스키마 검증 추가
- [ ] API 문서 업데이트

### Agent Gateway 팀

- [ ] Session Manager GET 응답에서 멀티턴 필드 추출
- [ ] Master Agent 호출 시 `session_context`로 매핑
- [ ] 펼침/중첩 `reference_information` 모두 처리
- [ ] `active_task`, `conversation_history`, `current_intent` 전달
- [ ] 통합 테스트 업데이트

### Master Agent 팀 (완료)

- [x] `session_context`에서 `active_task` 추출
- [x] `route_node`에서 DirectRouting에 활용
- [x] PATCH를 통해 Session Manager에 컨텍스트 저장
- [x] LLM 컨텍스트용 대화 이력 처리

---

## 7. 문의

이 명세서에 대한 문의:

- **Master Agent 팀**: 세션 컨텍스트 추출, DirectRouting 로직
- **Session Manager 팀**: 필드 저장, GET/PATCH 스키마
- **Agent Gateway 팀**: 컨텍스트 전달, 요청 매핑
