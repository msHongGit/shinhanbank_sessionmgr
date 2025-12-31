"""
Session Manager - Portal Schemas (Pydantic Models)
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ============ ListConversationsByPeriod ============

class ConversationFilters(BaseModel):
    """대화 목록 필터"""
    user_id: Optional[str] = Field(None, description="사용자 ID 필터")
    channel: Optional[str] = Field(None, description="채널 필터")
    session_id: Optional[str] = Field(None, description="세션 ID 필터")


class ConversationListItem(BaseModel):
    """대화 목록 아이템"""
    conversation_id: str = Field(..., description="대화 ID")
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    channel: str = Field(..., description="채널")
    started_at: datetime = Field(..., description="시작 시각")
    last_turn_at: datetime = Field(..., description="마지막 턴 시각")
    status: str = Field(..., description="상태")


class ConversationListData(BaseModel):
    """대화 목록 데이터"""
    items: List[ConversationListItem] = Field(..., description="대화 목록")
    cursor_next: Optional[str] = Field(None, description="다음 페이지 커서")
    total_count: int = Field(..., description="전체 건수")


class ConversationListResponse(BaseModel):
    """대화 목록 응답 (PORTAL-SM-01)"""
    success: bool = Field(..., description="성공 여부")
    data: Optional[ConversationListData] = Field(None, description="응답 데이터")
    error: Optional[dict] = Field(None, description="에러 정보")


# ============ GetConversationDetail ============

class ConversationTurn(BaseModel):
    """대화 턴"""
    turn_id: str = Field(..., description="턴 ID")
    role: Literal["user", "assistant", "system"] = Field(..., description="역할")
    text_masked: str = Field(..., description="마스킹된 텍스트")
    created_at: datetime = Field(..., description="생성 시각")
    outcome: Optional[str] = Field(None, description="결과")
    sa_status: Optional[str] = Field(None, description="SubAgent 상태")


class ConversationDetailData(BaseModel):
    """대화 상세 데이터"""
    conversation_id: str = Field(..., description="대화 ID")
    session_id: str = Field(..., description="세션 ID")
    items: List[ConversationTurn] = Field(..., description="턴 목록")
    cursor_next: Optional[str] = Field(None, description="다음 페이지 커서")


class ConversationDetailResponse(BaseModel):
    """대화 상세 응답 (PORTAL-SM-02)"""
    success: bool = Field(..., description="성공 여부")
    data: Optional[ConversationDetailData] = Field(None, description="응답 데이터")
    error: Optional[dict] = Field(None, description="에러 정보")


# ============ DeleteConversationHistory ============

class ConversationDeleteRequest(BaseModel):
    """대화 이력 삭제 요청 (PORTAL-SM-03)"""
    admin_id: str = Field(..., description="관리자 ID")
    reason: Optional[str] = Field(None, description="삭제 사유")


class ConversationDeleteData(BaseModel):
    """대화 삭제 데이터"""
    conversation_id: str = Field(..., description="대화 ID")
    deleted: bool = Field(..., description="삭제 완료 여부")


class ConversationDeleteResponse(BaseModel):
    """대화 이력 삭제 응답"""
    success: bool = Field(..., description="성공 여부")
    data: Optional[ConversationDeleteData] = Field(None, description="응답 데이터")
    error: Optional[dict] = Field(None, description="에러 정보")
