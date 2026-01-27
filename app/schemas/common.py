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

    user_id: str = Field(..., description="고객번호 (User ID, 숫자 10자리, 예: 0616001905)")
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

    global_session_key: str = Field(..., description="Global 세션 키")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")


class ErrorResponse(BaseModel):
    """에러 응답"""

    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    detail: str | None = Field(None, description="상세 정보")


class DialogTurn(BaseModel):
    """Sub-Agent 표준 스펙과 호환되는 대화 턴 (DialogTurn).

    Session Manager는 reference_information.conversation_history 를 기반으로
    이 구조를 구성하여 Master Agent/Agent Gateway에 전달할 수 있다.
    """

    role: str = Field(..., description="user | assistant | system")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime | None = Field(
        None,
        description="메시지 시각 (옵션; 문자열인 경우 ISO8601로 파싱 시도)",
    )
    agent_id: str | None = Field(
        None,
        alias="agentId",
        description="응답한 에이전트 ID (옵션)",
    )

    model_config = ConfigDict(populate_by_name=True)


class DialogContext(BaseModel):
    """Sub-Agent 표준 스펙과 호환되는 DialogContext.

    - turnId / turnCount / history / currentIntent / entities 구조를 따른다.
    - Session Manager GET 응답에서 옵션으로 제공하여, Agent Gateway가 그대로 사용 가능하도록 한다.
    """

    turn_id: str | None = Field(
        None,
        alias="turnId",
        description="현재 또는 마지막 턴 ID (옵션)",
    )
    turn_count: int | None = Field(
        None,
        alias="turnCount",
        description="현재 대화 턴 수 (옵션)",
    )
    history: list[DialogTurn] = Field(
        default_factory=list,
        description="대화 이력 (DialogTurn 목록)",
    )
    current_intent: str | None = Field(
        None,
        alias="currentIntent",
        description="현재 파악된 의도 (옵션)",
    )
    entities: dict[str, Any] | None = Field(
        None,
        description="추출된 엔티티 맵 (옵션)",
    )

    model_config = ConfigDict(populate_by_name=True)


class ChannelInfo(BaseModel):
    """세션 채널/이벤트 정보 (EventType, EventChannel).

    - eventType: 세션 진입 유형 (예: ICON_ENTRY)
    - eventChannel: 호출 채널 (예: web, kiosk 등)
    """

    event_type: str = Field(
        ...,
        alias="eventType",
        description="이벤트 유형 (세션 진입 유형)",
    )
    event_channel: str = Field(
        ...,
        alias="eventChannel",
        description="이벤트 채널 (기존 channel, 예: web, kiosk 등)",
    )

    model_config = ConfigDict(populate_by_name=True)


# ============================================================================
# Session Management Schemas (Merged from agw.py, ma.py)
# ============================================================================

# ============ Session Create (from agw.py) ============


class SessionCreateRequest(BaseModel):
    """초기 세션 생성 요청 (AGW → SM)

    Session Manager가 Global Session Key를 생성하여 반환하며,
    요청 바디는 userId 를 필수로 사용하고,
    channel 은 EventType / EventChannel 정보를 담는 딕셔너리로 사용한다.
    """

    user_id: str = Field(..., alias="userId", description="사용자 ID")
    channel: ChannelInfo | None = Field(
        None,
        description="채널/이벤트 정보 (eventType: 세션 진입 유형, eventChannel: 호출 채널)",
    )
    model_config = ConfigDict(populate_by_name=True)


class SessionCreateResponse(BaseModel):
    """초기 세션 생성 응답 (AGW에만 전달)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    jti: str = Field(..., description="JWT ID")


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
    user_id: str = Field(..., description="세션 사용자 ID")
    channel: ChannelInfo | None = Field(None, description="세션 채널/이벤트 정보 (EventType, EventChannel)")
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

    # 멀티턴 컨텍스트 필드 (mulititurn.md 옵션 A)
    active_task: dict[str, Any] | None = Field(
        None,
        description="DirectRouting용 활성 태스크 정보 (reference_information.active_task)",
    )
    conversation_history: list[dict[str, Any]] | None = Field(
        None,
        description="최근 대화 이력 (reference_information.conversation_history)",
    )
    current_intent: str | None = Field(
        None,
        description="현재 활성 의도 (reference_information.current_intent)",
    )
    current_task_id: str | None = Field(
        None,
        description="현재 태스크 ID (reference_information.current_task_id)",
    )
    task_queue_status_detail: list[dict[str, Any]] | None = Field(
        None,
        description="태스크 큐 상세 상태 (reference_information.task_queue_status)",
    )
    turn_count: int | None = Field(
        None,
        description="대화 턴 수 (reference_information.turn_count)",
    )

    # reference_information 전체 반환 (명세 외 필드 포함)
    reference_information: dict[str, Any] | None = Field(
        None,
        description="reference_information 전체 (명세 외 필드 포함)",
    )

    # PATCH 시 전달된 turn_id들을 누적 저장한 목록 (선택)
    turn_ids: list[str] | None = Field(
        None,
        description="해당 세션에서 PATCH로 기록된 turn_id 목록 (최신 순 또는 호출 순)",
    )

    # Sub-Agent 표준 스펙과 호환되는 DialogContext 뷰 (옵션)
    dialog_context: DialogContext | None = Field(
        None,
        description="Sub-Agent DialogContext와 호환되는 대화 컨텍스트 뷰 (옵션)",
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
    # MA 측에서 state_patch 최상위에 내려주는 멀티턴 필드 (향후 reference_information 안으로 정규화)
    current_intent: str | None = Field(
        None,
        description="현재 활성 의도 (MA가 state_patch.current_intent 로 보내는 값)",
    )
    turn_count: int | None = Field(
        None,
        description="대화 턴 수 (MA가 state_patch.turn_count 로 보내는 값)",
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
    """세션 생존 여부 확인 응답 (TTL 연장 없음)"""

    is_alive: bool = Field(..., description="세션이 살아있는지 여부")
    expires_at: datetime | None = Field(None, description="현재 만료 시각 (세션이 없으면 null, TTL 연장 안 함)")


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

    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")
    total_turns: int = Field(..., description="전체 턴 수")


class ConversationTurnSaveRequest(BaseModel):
    """대화 턴 저장 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
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


# ============ 실시간 API 연동 결과 저장 (Sprint 3+) ============


class TurnResponse(BaseModel):
    """턴 응답 (메타데이터 전용)"""

    turn_id: str
    global_session_key: str = Field(..., description="세션 키 (최상위 레벨에 명시적 포함)")
    turn_number: int | None = None
    role: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | str


class SolDBSTransactionPayload(BaseModel):
    """DBS 트랜잭션 요청 페이로드 (trxCd, dataBody)."""

    trx_cd: str = Field(..., alias="trxCd")
    data_body: str | dict[str, Any] = Field(..., alias="dataBody")

    model_config = ConfigDict(populate_by_name=True)


class SolDBSTransactionResult(BaseModel):
    """DBS 트랜잭션 응답 결과 (trxCd, responseData)."""

    trx_cd: str = Field(..., alias="trxCd")
    response_data: str | dict[str, Any] = Field(..., alias="responseData")

    model_config = ConfigDict(populate_by_name=True)


class SolApiResultRequest(BaseModel):
    """실시간 API 연동 결과 저장 요청.

    - sol_api.md 의 `/api/v1/sol/transaction`(RequestParam)
      + `/api/v1/sol/transaction/result`(DBSTrxResponse) 구조를 합친다.
    - 필드명은 SOL 측 스펙에 맞춰 camelCase alias를 사용한다.
    """

    # 필수 값
    global_session_key: str = Field(..., description="Global 세션 키 (Session Manager global_session_key)")
    turn_id: str = Field(..., description="턴 ID")

    # 선택 값 (SOL 측에서 상황에 따라 포함될 수도, 생략될 수도 있음)
    agent_id: str | None = Field(
        None,
        alias="agent",
        description="호출한 업무 Agent ID (다른 API의 agent_id 와 동일 의미)",
    )
    transaction_payload: list[SolDBSTransactionPayload] | None = Field(
        None,
        alias="transactionPayload",
        description="요청 시 사용된 DBS 전문 페이로드 목록 (없으면 생략 가능)",
    )

    glob_id: str | None = Field(None, alias="globId", description="GLOBALID (BXM 이벤트 ID, 옵션)")
    request_id: str | None = Field(None, alias="requestId", description="요청 식별자 (옵션)")
    result: str | None = Field(None, description="성공/실패 SUCCESS/FAIL (옵션)")
    result_code: str | None = Field(None, alias="resultCode", description="실패 코드 (옵션)")
    result_msg: str | None = Field(None, alias="resultMsg", description="실패 메시지 (옵션)")
    transaction_result: list[SolDBSTransactionResult] | None = Field(
        None,
        alias="transactionResult",
        description="DBS 전문 응답 결과 목록 (없으면 생략 가능)",
    )

    model_config = ConfigDict(populate_by_name=True)


class SessionFullResponse(BaseModel):
    """세션 전체 정보 응답 (세션 메타데이터 + 턴 목록)."""

    session: dict[str, Any] = Field(..., description="세션 메타데이터 (SessionResolveResponse 구조)")
    turns: list[dict[str, Any]] = Field(default_factory=list, description="턴 메타데이터 목록")
    total_turns: int = Field(..., description="전체 턴 수")


# ============ JWT Token Verification & Refresh ============


class SessionVerifyResponse(BaseModel):
    """토큰 검증 및 세션 정보 조회 응답"""

    global_session_key: str = Field(..., description="Global 세션 키")
    user_id: str = Field(..., description="사용자 ID")
    session_state: str = Field(..., description="세션 상태")
    is_alive: bool = Field(..., description="세션 생존 여부")
    expires_at: datetime | None = Field(None, description="만료 시각")


class TokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str | None = Field(None, description="Refresh Token (쿠키 또는 헤더에서 추출)")


class TokenRefreshResponse(BaseModel):
    """토큰 갱신 응답"""

    access_token: str = Field(..., description="새 Access Token")
    refresh_token: str = Field(..., description="새 Refresh Token")
    global_session_key: str = Field(..., description="Global 세션 키 (AGW에만 전달)")
    jti: str = Field(..., description="JWT ID")


# ============ 실시간 프로파일 ============


class RealtimePersonalContextRequest(BaseModel):
    """실시간 프로파일 업데이트 요청"""

    profile_data: dict[str, Any] = Field(
        ..., description="실시간 프로파일 데이터 (redis_data.md 구조 그대로 저장, 필드명 변경 없음)"
    )


class RealtimePersonalContextResponse(BaseModel):
    """실시간 프로파일 업데이트 응답"""

    status: str = Field(..., description="처리 상태")
    updated_at: datetime = Field(..., description="업데이트 시각")
