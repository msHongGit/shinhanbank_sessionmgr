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
    SessionPingResponse,
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

    필수 요청 필드:
    - userId: 세션을 식별할 사용자 ID

    선택 요청 필드:
    - channel: 이벤트/채널 정보 딕셔너리 (옵션)
        - eventType: 세션 진입 유형 (예: ICON_ENTRY)
        - eventChannel: 호출 채널 (예: web, kiosk 등)

    주요 응답 필드:
    - global_session_key: 이후 모든 호출에서 사용하는 세션 키 (그 외 메타데이터는 조회 API에서 확인)
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

    필수 경로 변수:
    - global_session_key: 조회할 세션 키

    선택 쿼리 파라미터:
    - agent_type, agent_id: 업무 Agent용 로컬 세션 키 조회에 사용

    주요 응답 필드:
    - global_session_key: 조회된 세션 키
    - channel: 세션 채널/이벤트 정보 (옵션)
        - eventType: 세션 진입 유형 (기존 startType)
        - eventChannel: 세션 채널 (기존 channel, web/kiosk 등)
    - session_state: 현재 세션 상태 (start/talk/end)
    - is_first_call: start 상태인지 여부
    - task_queue_status, subagent_status: 백엔드 작업/서브에이전트 상태
    - agent_session_key: (옵션) 업무 Agent 로컬 세션 키 매핑 결과
    - customer_profile: 세션에 저장된 고객 프로파일 (없으면 null)
    """,
)
async def get_session(
    global_session_key: str,
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
        agent_type=agent_type,
        agent_id=agent_id,
    )
    return service.resolve_session(request)


# ============ 세션 Ping (생존 확인 및 TTL 연장) ============


@router.get(
    "/{global_session_key}/ping",
    response_model=SessionPingResponse,
    summary="세션 생존 확인 및 TTL 연장",
    description="""
    세션이 살아있는지 간략히 조회하고, 살아있다면 TTL을 연장합니다.

    필수 경로 변수:
    - global_session_key: Ping 대상 세션 키

    주요 응답 필드:
    - is_alive: 세션 존재 여부 (false면 세션이 없거나 만료됨)
    - expires_at: TTL 연장 후 만료 예정 시각 (is_alive=false이면 null)
    """,
)
async def ping_session(
    global_session_key: str,
    service: SessionService = Depends(get_session_service),
):
    """세션 Ping API (헬스체크/TTL 연장용)."""
    return service.ping_session(global_session_key)


# ============ 세션 상태 업데이트 ============


@router.patch(
    "/{global_session_key}/state",
    response_model=SessionPatchResponse,
    summary="세션 상태 업데이트",
    description="""
        세션 상태를 업데이트합니다.

        필수 경로 변수:
        - global_session_key: 상태를 변경할 세션 키

        필수 요청 필드:
        - global_session_key: Path 변수와 동일해야 함

        선택 요청 필드 (Patch 방식):
        - session_state: 세션 상태 (start/talk/end) - 전송 시에만 변경
        - turn_id: 이 업데이트가 대응하는 턴 ID (이벤트 추적용)
        - state_patch: 업데이트할 세부 상태(서브에이전트 상태, 마지막 이벤트, session_attributes 등)

        session_state 값:
        - start: 세션 시작 상태
        - talk: 대화 진행 중 상태
        - end: 세션 종료 상태

        주요 동작:
        - SubAgent 상태, 마지막 이벤트, 세션 메타데이터(session_attributes) 업데이트
        - state_patch.agent_session_key + last_agent_id 가 함께 오면
            해당 Agent에 대한 Global↔Local 세션 매핑을 Redis에 등록
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

    필수 경로 변수:
    - global_session_key: 종료할 세션 키

    선택 쿼리 파라미터:
    - close_reason: 종료 사유 (user_exit, timeout 등)

    주요 응답 필드:
    - status: 처리 결과 (success)
    - closed_at: 세션 종료 시각
    - archived_conversation_id: 세션 기준 아카이브 ID (arch_{global_session_key})
    """,
)
async def close_session(
    global_session_key: str,
    close_reason: str | None = Query(None, description="종료 사유 (옵션)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 종료 API

    - MA: 대화 종료 시 호출
    - Client: 사용자가 앱 종료 시 호출
    """
    request = SessionCloseRequest(
        global_session_key=global_session_key,
        close_reason=close_reason,
    )
    return service.close_session(request, background_tasks)
