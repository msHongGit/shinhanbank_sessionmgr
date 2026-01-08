"""Context 및 Turn 관련 스키마."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Context 스키마
# ============================================================================


class ContextCreate(BaseModel):
    """컨텍스트 생성 요청"""

    context_id: str
    global_session_key: str
    user_id: str


class ContextUpdate(BaseModel):
    """컨텍스트 업데이트 요청"""

    summary: str | None = None
    current_intent: str | None = None
    current_slots: dict[str, Any] = Field(default_factory=dict)
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class ContextResponse(BaseModel):
    """컨텍스트 응답"""

    context_id: str
    global_session_key: str
    user_id: str
    summary: str | None = None
    current_intent: str | None = None
    current_slots: dict[str, Any] = Field(default_factory=dict)
    entities: list[str] = Field(default_factory=list)
    turn_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    last_updated_at: str


# =========================================================================
# Turn 스키마 (대화 텍스트 제외)
# ============================================================================


class TurnCreate(BaseModel):
    """턴 생성 요청 (메타데이터 전용)

    - 실제 사용자/Agent 대화 텍스트는 Session Manager에 저장하지 않음
    - turn_id, timestamp, metadata만 관리
    """

    turn_id: str = Field(..., description="턴 ID")
    timestamp: str = Field(..., description="타임스탬프 (ISO8601)")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="턴 메타데이터 (이벤트/상태/외부 API 결과 등)",
    )


class TurnCreateWithAPI(BaseModel):
    """API 호출 결과를 포함한 턴 생성 요청 (메타데이터 전용)

    - 텍스트는 저장하지 않고, API 호출 결과/에이전트 정보를 메타데이터로 관리
    """

    turn_id: str = Field(..., description="턴 ID")
    timestamp: str = Field(..., description="타임스탬프 (ISO8601)")
    agent_session_key: str | None = Field(None, description="에이전트 세션 키 (업무 Agent인 경우)")
    turn_number: int | None = Field(None, description="턴 번호 (optional, 없으면 자동 증가)")
    role: str = Field(default="system", description="역할 (예: system/external 등)")
    agent_id: str | None = Field(None, description="에이전트 ID")
    agent_type: str | None = Field(None, description="에이전트 타입")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="API 호출 결과 포함 메타데이터",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "turn_id": "turn_20260107_001",
                "timestamp": "2026-01-07T10:30:00Z",
                "agent_id": "dbs_caller",
                "agent_type": "external",
                "metadata": {
                    "api_call": {
                        "api_name": "get_exchange_rate",
                        "params": {"from": "KRW", "to": "USD"},
                        "result": {
                            "rate": 1320.5,
                            "timestamp": "2026-01-07T10:30:00Z",
                        },
                        "status": "success",
                        "duration_ms": 150,
                    }
                },
            }
        }
    )


class TurnResponse(BaseModel):
    """턴 응답 (메타데이터 전용)"""

    turn_id: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TurnListResponse(BaseModel):
    """턴 목록 응답"""

    context_id: str
    turns: list[TurnResponse]
    total_count: int
