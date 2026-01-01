"""
Session Manager - AGW Schemas (v3.0)
Agent GW → SM 요청/응답 스키마
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import SessionState


class SessionCreateRequest(BaseModel):
    """
    초기 세션 생성 요청 (AGW → SM)
    Client가 발급한 Global Session Key를 전달받아 세션 생성
    """
    global_session_key: str = Field(..., description="Client가 발급한 Global 세션 키")
    user_id: str = Field(..., description="사용자 ID")
    channel: str = Field(..., description="채널 (mobile, web, kiosk)")
    request_id: str | None = Field(None, description="요청 추적 ID (옵션)")
    device_info: dict[str, Any] | None = Field(None, description="디바이스 정보 (옵션)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "global_session_key": "gsess_20250316_user_1084756",
                "user_id": "user_1084756",
                "channel": "mobile",
                "device_info": {"type": "web", "browser": "Chrome"}
            }
        }
    )


class SessionCreateResponse(BaseModel):
    """초기 세션 생성 응답"""
    global_session_key: str = Field(..., description="Global 세션 키")
    conversation_id: str = Field(..., description="대화 ID")
    context_id: str = Field(..., description="Context ID (대화 이력 식별)")
    session_state: SessionState = Field(..., description="세션 상태")
    expires_at: datetime = Field(..., description="만료 시각")
    is_new: bool = Field(..., description="신규 생성 여부")
