"""
Session Manager - Portal Service
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.portal import (
    ConversationFilters,
    ConversationListResponse,
    ConversationListData,
    ConversationListItem,
    ConversationDetailResponse,
    ConversationDetailData,
    ConversationTurn,
    ConversationDeleteResponse,
    ConversationDeleteData,
)


class PortalService:
    """Portal 관리 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def list_conversations(
        self,
        admin_id: str,
        from_datetime: datetime,
        to_datetime: datetime,
        cursor: Optional[str] = None,
        limit: int = 50,
        filters: Optional[ConversationFilters] = None,
    ) -> ConversationListResponse:
        """대화 목록 조회"""
        # TODO: 실제 DB 조회 로직 구현
        # Mock 데이터 반환
        
        items = [
            ConversationListItem(
                conversation_id="conv_20250316_0019_001",
                session_id="sess_20250316_0019",
                user_id="user_1084756",
                channel="mobile",
                started_at=datetime(2025, 3, 16, 8, 40, 6),
                last_turn_at=datetime(2025, 3, 16, 8, 45, 0),
                status="end",
            ),
            ConversationListItem(
                conversation_id="conv_20250316_0020_001",
                session_id="sess_20250316_0020",
                user_id="user_1084757",
                channel="web",
                started_at=datetime(2025, 3, 16, 9, 0, 0),
                last_turn_at=datetime(2025, 3, 16, 9, 10, 0),
                status="talk",
            ),
        ]
        
        # 필터 적용
        if filters:
            if filters.user_id:
                items = [i for i in items if i.user_id == filters.user_id]
            if filters.channel:
                items = [i for i in items if i.channel == filters.channel]
            if filters.session_id:
                items = [i for i in items if i.session_id == filters.session_id]
        
        return ConversationListResponse(
            success=True,
            data=ConversationListData(
                items=items[:limit],
                cursor_next=None,
                total_count=len(items),
            ),
        )
    
    async def get_conversation_detail(
        self,
        admin_id: str,
        conversation_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> ConversationDetailResponse:
        """대화 상세 조회"""
        # TODO: 실제 DB 조회 로직 구현
        # Mock 데이터 반환
        
        items = [
            ConversationTurn(
                turn_id="turn_001",
                role="user",
                text_masked="채팅",
                created_at=datetime(2025, 3, 16, 8, 40, 6),
                outcome=None,
                sa_status=None,
            ),
            ConversationTurn(
                turn_id="turn_002",
                role="assistant",
                text_masked="문의하신 내용에 대한 정보를 찾았습니다.",
                created_at=datetime(2025, 3, 16, 8, 40, 8),
                outcome="normal",
                sa_status="end",
            ),
        ]
        
        return ConversationDetailResponse(
            success=True,
            data=ConversationDetailData(
                conversation_id=conversation_id,
                session_id="sess_20250316_0019",
                items=items[:limit],
                cursor_next=None,
            ),
        )
    
    async def delete_conversation(
        self,
        admin_id: str,
        conversation_id: str,
        reason: Optional[str] = None,
    ) -> ConversationDeleteResponse:
        """대화 이력 삭제"""
        # TODO: 실제 삭제 로직 구현
        # 1. 이력 존재 확인
        # 2. 삭제 처리
        # 3. 감사 로그 기록
        
        return ConversationDeleteResponse(
            success=True,
            data=ConversationDeleteData(
                conversation_id=conversation_id,
                deleted=True,
            ),
        )
