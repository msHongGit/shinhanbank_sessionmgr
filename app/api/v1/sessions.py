"""
Session Manager - Unified Sessions API
통합 세션 API: 기능별 분리, 인증으로 호출자 구분
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.core.auth import APIKeyType, require_api_key
from app.schemas.common import (
    AgentType,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============ 의존성 ============


def get_session_service() -> SessionService:
    """SessionService 의존성"""
    return SessionService()


# ============ 세션 생성 ============


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=201,
    summary="세션 생성",
    description="""
    세션을 생성합니다.

    - 새 세션 생성 시 conversation_id, context_id 발급
    - 기존 세션이 유효하면 기존 정보 반환 (is_new=false)
    """,
)
async def create_session(
    request: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    service: SessionService = Depends(get_session_service),
):
    """
    세션 생성 API

    - AGW: Agent Gateway가 초기 세션 생성
    - Client: 사용자 앱이 직접 세션 생성
    - 프로파일 자동 조회: user_id로 Profile DB에서 프로파일 조회 및 세션에 포함
    """
    return service.create_session(request, background_tasks)


# ============ 세션 조회 ============


@router.get(
    "/{global_session_key}",
    response_model=SessionResolveResponse,
    summary="세션 조회",
    description="""
    세션을 조회합니다.

    - 세션 상태, Task Queue 상태, SubAgent 상태 등 반환
    - 업무 Agent인 경우 Global↔Local 매핑도 조회
    """,
)
async def get_session(
    global_session_key: str,
    channel: str | None = Query(None, description="채널 (옵션)"),
    agent_type: AgentType | None = Query(None, description="Agent 유형 (옵션)"),
    agent_id: str | None = Query(None, description="Agent ID (옵션)"),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 조회 API

    - MA: 세션 상태, SubAgent 상태 조회
    - Portal: 관리자 조회
    - Client: 사용자 세션 조회
    """
    request = SessionResolveRequest(
        global_session_key=global_session_key,
        channel=channel,
        agent_type=agent_type,
        agent_id=agent_id,
    )
    return service.resolve_session(request)


# ============ 세션 상태 업데이트 ============


@router.patch(
    "/{global_session_key}/state",
    response_model=SessionPatchResponse,
    summary="세션 상태 업데이트",
    description="""
    세션 상태를 업데이트합니다.

    - SubAgent 상태, 마지막 이벤트 등 업데이트
    - SA 응답 후 MA가 호출
    """,
)
async def update_session_state(
    global_session_key: str,
    request: SessionPatchRequest,
    background_tasks: BackgroundTasks,
    service: SessionService = Depends(get_session_service),
):
    """
    세션 상태 업데이트 API (MA 전용)

    - 세션 상태 전이 (Policy 검증 포함)
    - SubAgent 상태 업데이트
    """
    # global_session_key는 path에서도 받고 body에도 있어야 하므로 검증
    if request.global_session_key != global_session_key:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="global_session_key mismatch")

    return service.patch_session_state(request, background_tasks)


# ============ 세션 종료 ============


@router.delete(
    "/{global_session_key}",
    response_model=SessionCloseResponse,
    summary="세션 종료",
    description="""
    세션을 종료합니다.

    - 세션 상태를 'end'로 변경
    """,
)
async def close_session(
    global_session_key: str,
    conversation_id: str | None = Query(None, description="대화 ID (옵션)"),
    close_reason: str | None = Query(None, description="종료 사유 (옵션)"),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 종료 API

    - MA: 대화 종료 시 호출
    - Client: 사용자가 앱 종료 시 호출
    """
    request = SessionCloseRequest(
        global_session_key=global_session_key,
        conversation_id=conversation_id,
        close_reason=close_reason,
    )
    return service.close_session(request)
