"""
Session Manager - Portal Schemas (v3.0)
Portal → SM 요청/응답 스키마
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import SessionState

# ============ 세션 목록 조회 (읽기 전용) ============

class SessionListItem(BaseModel):
    """세션 목록 아이템"""
    global_session_key: str
    user_id: str
    channel: str
    session_state: SessionState
    context_id: str
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None


class SessionListResponse(BaseModel):
    """세션 목록 조회 응답"""
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    items: list[SessionListItem] = Field(default=[], description="세션 목록")


# ============ Context 삭제 (대화 이력) ============

class ContextDeleteRequest(BaseModel):
    """
    Context 삭제 요청 (Portal → SM)
    context_id 기준으로 대화 이력 삭제
    """
    context_id: str = Field(..., description="삭제할 Context ID")
    reason: str | None = Field(None, description="삭제 사유")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "context_id": "ctx_20250316_user_001",
                "reason": "사용자 요청에 의한 삭제"
            }
        }
    )


class ContextDeleteResponse(BaseModel):
    """Context 삭제 응답"""
    status: str = Field(..., description="처리 상태")
    context_id: str = Field(..., description="삭제된 Context ID")
    deleted_turns: int = Field(..., description="삭제된 대화 턴 수")
    deleted_at: datetime = Field(..., description="삭제 시각")


# ============ Context 조회 ============

class ContextInfoResponse(BaseModel):
    """Context 정보 조회 응답"""
    context_id: str
    global_session_key: str
    user_id: str
    turn_count: int
    created_at: datetime
    last_updated_at: datetime
