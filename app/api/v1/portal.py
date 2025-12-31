"""
Session Manager - Portal Management API Endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.schemas.portal import (
    ConversationFilters,
    ConversationListResponse,
    ConversationDetailResponse,
    ConversationDeleteRequest,
    ConversationDeleteResponse,
)
from app.services.portal_service import PortalService
from app.api.deps import get_portal_service, verify_api_key

router = APIRouter(prefix="/portal", tags=["Portal"])


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="대화 목록 조회",
    description="기간별 대화 이력 목록을 조회합니다. (PORTAL-SM-01)"
)
async def list_conversations(
    admin_id: str = Query(..., description="관리자 ID"),
    from_datetime: datetime = Query(..., description="조회 시작 일시"),
    to_datetime: datetime = Query(..., description="조회 종료 일시"),
    cursor: Optional[str] = Query(None, description="페이지네이션 커서"),
    limit: int = Query(50, ge=1, le=100, description="조회 건수"),
    user_id: Optional[str] = Query(None, description="사용자 ID 필터"),
    channel: Optional[str] = Query(None, description="채널 필터"),
    session_id: Optional[str] = Query(None, description="세션 ID 필터"),
    service: PortalService = Depends(get_portal_service),
    api_key: str = Depends(verify_api_key),
):
    """
    대화 목록 조회 API
    
    - **admin_id**: 관리자 ID
    - **from_datetime**: 조회 시작 일시
    - **to_datetime**: 조회 종료 일시
    - **filters**: 필터 조건 (user_id, channel, session_id)
    """
    filters = ConversationFilters(
        user_id=user_id,
        channel=channel,
        session_id=session_id,
    )
    return await service.list_conversations(
        admin_id=admin_id,
        from_datetime=from_datetime,
        to_datetime=to_datetime,
        cursor=cursor,
        limit=limit,
        filters=filters,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="대화 상세 조회",
    description="특정 대화의 상세 내용을 조회합니다. (PORTAL-SM-02)"
)
async def get_conversation_detail(
    conversation_id: str,
    admin_id: str = Query(..., description="관리자 ID"),
    cursor: Optional[str] = Query(None, description="페이지네이션 커서"),
    limit: int = Query(50, ge=1, le=100, description="조회 건수"),
    service: PortalService = Depends(get_portal_service),
    api_key: str = Depends(verify_api_key),
):
    """
    대화 상세 조회 API
    
    - **conversation_id**: 대화 ID
    - **admin_id**: 관리자 ID
    """
    return await service.get_conversation_detail(
        admin_id=admin_id,
        conversation_id=conversation_id,
        cursor=cursor,
        limit=limit,
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ConversationDeleteResponse,
    summary="대화 이력 삭제",
    description="대화 이력을 삭제합니다. (PORTAL-SM-03)"
)
async def delete_conversation(
    conversation_id: str,
    request: ConversationDeleteRequest,
    service: PortalService = Depends(get_portal_service),
    api_key: str = Depends(verify_api_key),
):
    """
    대화 이력 삭제 API
    
    - **conversation_id**: 삭제할 대화 ID
    - **admin_id**: 관리자 ID
    - **reason**: 삭제 사유
    """
    return await service.delete_conversation(
        admin_id=request.admin_id,
        conversation_id=conversation_id,
        reason=request.reason,
    )
