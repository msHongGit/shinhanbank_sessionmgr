"""Deprecated Agent Session Schemas.

Unified Sessions API 의 세션 상태 PATCH 로 Agent 세션 매핑을
처리하도록 변경되면서, 이 스키마들은 더 이상 사용되지 않습니다.

향후 DB 기반 `agent_sessions` 테이블을 다시 노출해야 할 때
필요시 재도입하기 위한 빈 스텁 모듈로 남겨둡니다.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import AgentType


class AgentSessionGetResponse(BaseModel):
    """에이전트 세션 조회 응답"""

    global_session_key: str
    agent_session_key: str | None = Field(None, description="없으면 null")
    agent_id: str
    agent_type: AgentType | None = None
    is_active: bool = Field(..., description="활성 상태 여부")
    created_at: datetime
    last_used_at: datetime
