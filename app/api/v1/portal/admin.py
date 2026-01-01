"""
Session Manager - Portal API (v4.0)
Portal → SM
세션 조회 (읽기 전용), Context 삭제
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_context_service, get_session_service, verify_portal_api_key
from app.schemas import SessionState
from app.schemas.portal import (
    ContextDeleteRequest,
    ContextDeleteResponse,
    ContextInfoResponse,
    SessionListResponse,
)
from app.services.context_service import ContextService
from app.services.session_service import SessionService

router = APIRouter(prefix="/portal", tags=["Portal - Admin"])


# ============ 세션 조회 (읽기 전용) ============

@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="세션 목록 조회",
    description="""
    Portal에서 세션 목록을 조회합니다. (읽기 전용)
    
    - 필터링: user_id, session_state
    - 페이징 지원
    - 세션 삭제는 불가
    """
)
def list_sessions(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    user_id: str | None = Query(None, description="사용자 ID 필터"),
    session_state: SessionState | None = Query(None, description="세션 상태 필터"),
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_portal_api_key),
):
    return service.list_sessions(page, page_size, user_id, session_state)


# ============ Context 관리 ============

@router.get(
    "/context/{context_id}",
    response_model=ContextInfoResponse,
    summary="Context 정보 조회",
    description="Context(대화 이력) 정보를 조회합니다."
)
def get_context_info(
    context_id: str,
    service: ContextService = Depends(get_context_service),
    api_key: str = Depends(verify_portal_api_key),
):
    return service.get_context_info(context_id)


@router.delete(
    "/context/{context_id}",
    response_model=ContextDeleteResponse,
    summary="Context 삭제",
    description="""
    Context(대화 이력)를 삭제합니다.
    
    - context_id 기준으로 대화 이력 삭제
    - 세션 자체는 삭제되지 않음
    """
)
def delete_context(
    context_id: str,
    reason: str | None = Query(None, description="삭제 사유"),
    service: ContextService = Depends(get_context_service),
    api_key: str = Depends(verify_portal_api_key),
):
    request = ContextDeleteRequest(context_id=context_id, reason=reason)
    return service.delete_context(request)
