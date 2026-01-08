"""
Session Manager - Agent Session Schemas
에이전트 세션 (구 Local Session) 스키마
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AgentType


class AgentSessionRegisterRequest(BaseModel):
    """에이전트 세션 등록 요청 (MA → SM) - 업무 Agent Start 후"""

    global_session_key: str = Field(..., description="Global 세션 키")
    agent_session_key: str = Field(..., description="업무 Agent가 발급한 에이전트 세션 키")
    agent_id: str = Field(..., description="업무 Agent ID")
    agent_type: AgentType = Field(AgentType.TASK, description="Agent 유형")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "global_session_key": "gsess_20260107_user_001",
                "agent_session_key": "asess_agent_transfer_001",
                "agent_id": "agent-transfer",
                "agent_type": "task",
            }
        }
    )


class AgentSessionRegisterResponse(BaseModel):
    """에이전트 세션 등록 응답"""

    status: str = Field(..., description="처리 상태")
    mapping_id: str = Field(..., description="매핑 ID")
    expires_at: datetime = Field(..., description="매핑 만료 시각")


class AgentSessionGetResponse(BaseModel):
    """에이전트 세션 조회 응답"""

    global_session_key: str
    agent_session_key: str | None = Field(None, description="없으면 null")
    agent_id: str
    agent_type: AgentType | None = None
    is_active: bool = Field(..., description="활성 상태 여부")
    created_at: datetime
    last_used_at: datetime
