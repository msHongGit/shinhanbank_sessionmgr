"""
Session Manager - MA Session API (v4.0)
MA → SM 세션 관리
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_session_service, verify_ma_api_key
from app.schemas import AgentType
from app.schemas.ma import (
    LocalSessionGetResponse,
    LocalSessionRegisterRequest,
    LocalSessionRegisterResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/ma/sessions", tags=["MA - Session Management"])


@router.get(
    "/resolve",
    response_model=SessionResolveResponse,
    summary="세션 조회",
    description="""
    MA가 세션을 조회합니다.
    
    - 세션 상태, Task Queue 상태, SubAgent 상태 등 반환
    - 업무 Agent인 경우 Global↔Local 매핑도 조회
    """
)
def resolve_session(
    global_session_key: str = Query(..., description="Global 세션 키"),
    channel: str | None = Query(None, description="채널 (옵션)"),
    agent_type: AgentType | None = Query(None, description="Agent 유형"),
    agent_id: str | None = Query(None, description="Agent ID (업무 Agent용)"),
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_ma_api_key),
):
    request = SessionResolveRequest(
        global_session_key=global_session_key,
        channel=channel,
        agent_type=agent_type,
        agent_id=agent_id
    )
    return service.resolve_session(request)


@router.post(
    "/local",
    response_model=LocalSessionRegisterResponse,
    status_code=201,
    summary="Local 세션 등록",
    description="""
    업무 Agent Start 후 Local 세션을 등록합니다.
    
    - Global↔Local 세션 매핑 생성
    - 이후 MA는 이 매핑을 조회하여 Local 세션 키로 업무 Agent 호출
    """
)
def register_local_session(
    request: LocalSessionRegisterRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.register_local_session(request)


@router.get(
    "/local",
    response_model=LocalSessionGetResponse,
    summary="Local 세션 조회",
    description="Global 세션 키로 Local 세션 키를 조회합니다."
)
def get_local_session(
    global_session_key: str = Query(..., description="Global 세션 키"),
    agent_id: str = Query(..., description="Agent ID"),
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.get_local_session(global_session_key, agent_id)


@router.patch(
    "/state",
    response_model=SessionPatchResponse,
    summary="세션 상태 업데이트",
    description="""
    MA가 세션 상태를 업데이트합니다.
    
    - SubAgent 상태, 마지막 이벤트 등 업데이트
    - SA 응답 후 MA가 호출
    """
)
def patch_session_state(
    request: SessionPatchRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.patch_session_state(request)


@router.post(
    "/close",
    response_model=SessionCloseResponse,
    summary="세션 종료",
    description="""
    세션을 종료합니다.
    
    - 세션 상태를 'end'로 변경
    - 모든 Local 세션 매핑 삭제
    - Task Queue 정리
    """
)
def close_session(
    request: SessionCloseRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.close_session(request)
