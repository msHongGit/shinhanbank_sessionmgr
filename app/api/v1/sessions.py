"""
Session Manager - Session API Endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from typing import Optional

from app.schemas.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionKey,
)
from app.services.session_service import SessionService
from app.api.deps import get_session_service, verify_api_key

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=201,
    summary="초기 세션 생성",
    description="AGW가 최초 진입 시 초기 세션을 생성합니다. (AGW-SM-01)"
)
async def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_api_key),
):
    """
    초기 세션 생성 API
    
    - **user_id**: 사용자 고유 식별자
    - **channel**: 채널 (mobile, web, kiosk 등)
    - **session_key**: 세션 키 {scope, key}
    - **request_id**: 요청 추적용 ID
    """
    return await service.create_session(request)


@router.get(
    "/resolve",
    response_model=SessionResolveResponse,
    summary="세션 조회/생성",
    description="MA가 세션을 조회하고 현재 상태를 획득합니다. (MA-SM-01)"
)
async def resolve_session(
    session_key_scope: str = Query(..., description="세션 키 범위 (global/local)"),
    session_key_value: str = Query(..., description="세션 키 값"),
    channel: str = Query(..., description="채널"),
    conversation_id: Optional[str] = Query(None, description="대화 ID"),
    user_id_ref: Optional[str] = Query(None, description="사용자 ID 참조"),
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_api_key),
):
    """
    세션 조회/생성 API
    
    - 세션이 없으면 자동 생성
    - Redis 캐시 우선 조회, 없으면 PostgreSQL 조회
    """
    request = SessionResolveRequest(
        session_key=SessionKey(scope=session_key_scope, key=session_key_value),
        channel=channel,
        conversation_id=conversation_id,
        user_id_ref=user_id_ref,
    )
    return await service.resolve_session(request)


@router.patch(
    "/{session_id}",
    response_model=SessionPatchResponse,
    summary="세션 상태 업데이트",
    description="MA가 세션 상태를 업데이트합니다. (MA-SM-02)"
)
async def patch_session_state(
    session_id: str,
    request: SessionPatchRequest,
    background_tasks: BackgroundTasks,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_api_key),
):
    """
    세션 상태 업데이트 API
    
    - Redis 캐시 업데이트 (동기)
    - PostgreSQL 스냅샷 저장 (비동기)
    """
    return await service.patch_session_state(session_id, request, background_tasks)


@router.post(
    "/{session_id}/close",
    response_model=SessionCloseResponse,
    summary="세션 종료",
    description="세션을 종료하고 메타정보를 취합합니다. (MA-SM-03)"
)
async def close_session(
    session_id: str,
    request: SessionCloseRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_api_key),
):
    """
    세션 종료 API
    
    - 세션 상태를 'end'로 변경
    - Task Queue 정리
    - 대화 이력 아카이브
    """
    return await service.close_session(session_id, request)
