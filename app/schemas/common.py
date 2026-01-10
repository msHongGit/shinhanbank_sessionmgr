"""
Session Manager - Common Schemas (v3.0)
SM에서 사용하는 공통 타입 정의
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============ Enums ============


class SessionState(str, Enum):
    """세션 상태"""

    START = "start"
    TALK = "talk"
    END = "end"


class AgentType(str, Enum):
    """Agent 유형"""

    KNOWLEDGE = "knowledge"  # 지식 Agent
    TASK = "task"  # 업무 Agent


class ResponseType(str, Enum):
    """SA 응답 타입 (SM이 기록용으로 사용)"""

    CONTINUE = "continue"
    END = "end"
    FALLBACK = "fallback"


class FallbackReason(str, Enum):
    """Fallback 사유 코드"""

    INTENT_ERROR = "INTENT_ERROR"
    SLOT_FILLING_FAIL = "SLOT_FILLING_FAIL"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class TaskQueueStatus(str, Enum):
    """Task Queue 상태"""

    NULL = "null"
    NOTNULL = "notnull"


class SubAgentStatus(str, Enum):
    """SubAgent 상태"""

    UNDEFINED = "undefined"
    CONTINUE = "continue"
    END = "end"


class SessionStatus(BaseModel):
    """세션 상태 구조 (요구사항 기반)"""

    global_session_key: str
    user_id: str

    # Event tracking
    event_source: str | None = None
    event_type: str | None = None

    # Status fields
    conversation_status: SessionState  # start | talk | end
    task_queue_status: TaskQueueStatus
    subagent_status: SubAgentStatus

    # Ownership and context
    action_owner: str | None = None
    reference_information: dict[str, Any] = Field(default_factory=dict)
    custom_message: str | None = None

    # Timestamps
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============ Common Models ============


class ProfileAttribute(BaseModel):
    """고객 프로파일 속성"""

    key: str = Field(..., description="속성 키")
    value: str = Field(..., description="속성 값")
    source_system: str = Field(..., description="소스 시스템")
    valid_from: str | None = Field(None, description="유효 시작일")
    valid_to: str | None = Field(None, description="유효 종료일")


class CustomerProfile(BaseModel):
    """고객 프로파일"""

    user_id: str = Field(..., description="사용자 ID")
    attributes: list[ProfileAttribute] = Field(default=[], description="속성 목록")
    segment: str | None = Field(None, description="고객 세그먼트")
    preferences: dict[str, Any] | None = Field(None, description="고객 선호 설정")


class ConversationTurn(BaseModel):
    """대화 턴"""

    turn_id: str = Field(..., description="턴 ID")
    role: str = Field(..., description="user | assistant")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime = Field(..., description="메시지 시각")


class ConversationHistory(BaseModel):
    """대화 이력"""

    context_id: str = Field(..., description="Context ID")
    global_session_key: str = Field(..., description="Global 세션 키")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")


class ErrorResponse(BaseModel):
    """에러 응답"""

    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    detail: str | None = Field(None, description="상세 정보")


# ============================================================================
# Session Management Schemas (Merged from agw.py, ma.py)
# ============================================================================

# ============ Session Create (from agw.py) ============


class SessionCreateRequest(BaseModel):
    """초기 세션 생성 요청 (AGW → SM)

    Session Manager가 Global Session Key를 생성하여 반환하며,
    요청 바디는 userId, startType 두 필드만 사용한다.
    """

    user_id: str = Field(..., alias="userId", description="사용자 ID")
    start_type: str = Field(
        ...,
        alias="startType",
        description="세션 진입 유형 (예: ICON_ENTRY, SOL_PAGE_ENTRY 등)",
    )

    model_config = ConfigDict(populate_by_name=True)


class SessionCreateResponse(BaseModel):
    """초기 세션 생성 응답"""

    # 외부 응답은 Global 세션 키만 노출 (나머지 메타데이터는 내부/조회용)
    global_session_key: str = Field(..., description="Global 세션 키")


# ============ Session Resolve (from ma.py) ============


class SessionResolveRequest(BaseModel):
    """세션 조회 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    channel: str | None = Field(None, description="채널 (옵션)")
    agent_type: AgentType | None = Field(None, description="호출할 Agent 유형")
    agent_id: str | None = Field(None, description="호출할 Agent ID")


class LastEvent(BaseModel):
    """마지막 이벤트 정보"""

    event_type: str
    agent_id: str | None = None
    agent_type: AgentType | None = None
    response_type: ResponseType | None = None
    updated_at: datetime


class SessionResolveResponse(BaseModel):
    """세션 조회 응답"""

    global_session_key: str = Field(..., description="Global 세션 키")
    agent_session_key: str | None = Field(None, description="업무 Agent 세션 키")
    session_state: SessionState = Field(..., description="세션 상태")
    is_first_call: bool = Field(..., description="최초 호출 여부")
    task_queue_status: TaskQueueStatus = Field(..., description="Task Queue 상태")
    subagent_status: SubAgentStatus = Field(..., description="SubAgent 상태")
    last_event: LastEvent | None = Field(None, description="마지막 이벤트")
    customer_profile: CustomerProfile | None = Field(
        None,
        description="세션에 연결된 고객 프로파일 (옵션)",
    )


# ============ Session State Update (from ma.py) ============


class StatePatch(BaseModel):
    """세션 상태 패치 데이터"""

    subagent_status: SubAgentStatus | None = None
    action_owner: str | None = None
    reference_information: dict[str, Any] | None = None
    cushion_message: str | None = None
    last_agent_id: str | None = None
    last_agent_type: AgentType | None = None
    last_response_type: ResponseType | None = None
    agent_session_key: str | None = None
    session_attributes: dict[str, Any] | None = Field(
        None,
        description="MA에서 추가로 세션에 저장하고 싶은 임의의 속성 맵",
    )


class SessionPatchRequest(BaseModel):
    """세션 상태 업데이트 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    turn_id: str | None = Field(None, description="턴 ID (옵션; 이벤트 추적용)")
    session_state: SessionState | None = Field(None, description="세션 상태 (옵션; 변경 시에만 전송)")
    state_patch: StatePatch | None = Field(None, description="상태 패치 데이터 (옵션)")


class SessionPatchResponse(BaseModel):
    """세션 상태 업데이트 응답"""

    status: str = Field(..., description="처리 상태")
    updated_at: datetime = Field(..., description="업데이트 시각")


class SessionPingResponse(BaseModel):
    """세션 생존 여부 및 TTL 연장 응답"""

    global_session_key: str = Field(..., description="Global 세션 키")
    is_alive: bool = Field(..., description="세션이 살아있는지 여부")
    expires_at: datetime | None = Field(None, description="연장 후 만료 시각 (세션이 없으면 null)")


# ============ Session Close (from ma.py) ============


class SessionCloseRequest(BaseModel):
    """세션 종료 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    close_reason: str | None = Field(None, description="종료 사유 (user_exit, timeout, transfer 등)")
    final_summary: str | None = Field(None, description="최종 요약")


class SessionCloseResponse(BaseModel):
    """세션 종료 응답"""

    status: str
    closed_at: datetime
    archived_conversation_id: str
    cleaned_local_sessions: int = Field(..., description="정리된 Local 세션 수")


# ============ Conversation History (from ma.py) ============


class ConversationHistoryResponse(BaseModel):
    """대화 이력 조회 응답"""

    context_id: str = Field(..., description="Context ID")
    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")
    total_turns: int = Field(..., description="전체 턴 수")


class ConversationTurnSaveRequest(BaseModel):
    """대화 턴 저장 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    context_id: str = Field(..., description="Context ID")
    turn: ConversationTurn = Field(..., description="저장할 턴")


class ConversationTurnSaveResponse(BaseModel):
    """대화 턴 저장 응답"""

    status: str
    turn_id: str
    saved_at: datetime


# ============ Profile (from ma.py) ============


class ProfileGetResponse(BaseModel):
    """고객 프로파일 조회 응답"""

    user_id: str
    profile: CustomerProfile
    computed_at: datetime
