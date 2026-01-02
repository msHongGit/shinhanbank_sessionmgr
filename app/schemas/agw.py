"""
Session Manager - AGW Schemas (v3.0)
Agent GW → SM 요청/응답 스키마
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CustomerProfile, SessionState


class SessionCreateRequest(BaseModel):
    """
    초기 세션 생성 요청 (AGW → SM)
    Session Manager가 Global Session Key를 생성하여 반환
    """

    user_id: str = Field(..., description="사용자 ID")
    channel: str = Field(..., description="채널 (mobile, web, kiosk)")
    request_id: str | None = Field(None, description="요청 추적 ID (옵션)")
    device_info: dict[str, Any] | None = Field(None, description="디바이스 정보 (옵션)")
    customer_profile: CustomerProfile | None = Field(
        None,
        description="고객 개인화 프로파일 스냅샷 (옵션, Demo 시 세션과 함께 전달)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user_1084756",
                "channel": "mobile",
                "device_info": {"type": "web", "browser": "Chrome"},
                "customer_profile": {
                    "user_id": "user_1084756",
                    "segment": "VIP",
                    "attributes": [
                        {"key": "tier", "value": "platinum", "source_system": "CRM"},
                        {"key": "preferred_language", "value": "ko", "source_system": "CRM"},
                    ],
                    "preferences": {"language": "ko"},
                },
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
    customer_profile: CustomerProfile | None = Field(
        None,
        description="세션에 저장된 고객 프로파일 (옵션)",
    )
