"""
Session Manager - MA Schemas (v3.0)
MA → SM 요청/응답 스키마
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AgentType, ConversationTurn, CustomerProfile, ResponseType, SessionState, SubAgentStatus, TaskQueueStatus

# ============ ResolveSession ============


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
    local_session_key: str | None = Field(None, description="Local 세션 키 (업무 Agent)")
    conversation_id: str = Field(..., description="대화 ID")
    context_id: str = Field(..., description="Context ID")
    session_state: SessionState = Field(..., description="세션 상태")
    is_first_call: bool = Field(..., description="최초 호출 여부")
    task_queue_status: TaskQueueStatus = Field(..., description="Task Queue 상태")
    subagent_status: SubAgentStatus = Field(..., description="SubAgent 상태")
    last_event: LastEvent | None = Field(None, description="마지막 이벤트")
    customer_profile_ref: str | None = Field(None, description="고객 프로파일 참조")


# ============ Local Session 등록/조회 ============


class LocalSessionRegisterRequest(BaseModel):
    """Local 세션 등록 요청 (MA → SM) - 업무 Agent Start 후"""

    global_session_key: str = Field(..., description="Global 세션 키")
    local_session_key: str = Field(..., description="업무 Agent가 발급한 Local 세션 키")
    agent_id: str = Field(..., description="업무 Agent ID")
    agent_type: AgentType = Field(AgentType.TASK, description="Agent 유형")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "global_session_key": "gsess_20250316_user_001",
                "local_session_key": "lsess_agent_transfer_001",
                "agent_id": "agent-transfer",
                "agent_type": "task",
            }
        }
    )


class LocalSessionRegisterResponse(BaseModel):
    """Local 세션 등록 응답"""

    status: str = Field(..., description="처리 상태")
    mapping_id: str = Field(..., description="매핑 ID")
    expires_at: datetime = Field(..., description="매핑 만료 시각")


class LocalSessionGetResponse(BaseModel):
    """Local 세션 조회 응답"""

    global_session_key: str
    local_session_key: str | None = Field(None, description="없으면 null")
    agent_id: str
    agent_type: AgentType | None = None
    is_active: bool = Field(..., description="활성 상태 여부")


# ============ 세션 상태 업데이트 ============


class StatePatch(BaseModel):
    """세션 상태 패치 데이터"""

    subagent_status: SubAgentStatus | None = None
    action_owner: str | None = None
    reference_information: dict[str, Any] | None = None
    cushion_message: str | None = None
    last_agent_id: str | None = None
    last_agent_type: AgentType | None = None
    last_response_type: ResponseType | None = None


class SessionPatchRequest(BaseModel):
    """세션 상태 업데이트 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    turn_id: str = Field(..., description="턴 ID")
    session_state: SessionState = Field(..., description="세션 상태")
    state_patch: StatePatch = Field(..., description="상태 패치 데이터")


class SessionPatchResponse(BaseModel):
    """세션 상태 업데이트 응답"""

    status: str = Field(..., description="처리 상태")
    updated_at: datetime = Field(..., description="업데이트 시각")


# ============ 세션 종료 ============


class SessionCloseRequest(BaseModel):
    """세션 종료 요청 (MA → SM)"""

    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    close_reason: str = Field(..., description="종료 사유 (user_exit, timeout, transfer)")
    final_summary: str | None = Field(None, description="최종 요약")


class SessionCloseResponse(BaseModel):
    """세션 종료 응답"""

    status: str
    closed_at: datetime
    archived_conversation_id: str
    cleaned_local_sessions: int = Field(..., description="정리된 Local 세션 수")


# ============ 대화 이력 조회 ============


class ConversationHistoryResponse(BaseModel):
    """대화 이력 조회 응답"""

    context_id: str = Field(..., description="Context ID")
    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")
    total_turns: int = Field(..., description="전체 턴 수")


# ============ 대화 이력 저장 ============


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


# ============ 고객 프로파일 조회 ============


class ProfileGetResponse(BaseModel):
    """고객 프로파일 조회 응답"""

    user_id: str
    profile: CustomerProfile
    computed_at: datetime
