"""
Session Manager - Agent Sessions API
MA 전용: Global ↔ Agent 세션 매핑 관리
"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import APIKeyType, require_api_key
from app.schemas.agent_sessions import (
    AgentSessionGetResponse,
    AgentSessionRegisterRequest,
    AgentSessionRegisterResponse,
)
from app.services.session_service import SessionService

router = APIRouter(prefix="/agent-sessions", tags=["Agent Sessions (MA Only)"])


# ============ 의존성 ============


def get_session_service() -> SessionService:
    """SessionService 의존성"""
    return SessionService()


# ============ Agent 세션 매핑 등록 ============


@router.post(
    "",
    response_model=AgentSessionRegisterResponse,
    status_code=201,
    summary="Agent 세션 등록",
    description="""
    MA 전용: 업무 Agent Start 후 Agent 세션을 등록합니다.
    
    **허용 호출자**: MA만
    
    - Global↔Agent 세션 매핑 생성
    - 이후 MA는 이 매핑을 조회하여 Agent 세션 키로 업무 Agent 호출
    """,
)
async def register_agent_session(
    request: AgentSessionRegisterRequest,
    service: SessionService = Depends(get_session_service),
    caller: APIKeyType = Depends(require_api_key([APIKeyType.MA])),
):
    """
    Agent 세션 등록 (MA 전용)

    MA가 내부 SubAgent의 세션 ID를 글로벌 세션과 연결합니다:
    - Talk Agent: talk_session_001
    - Task Agent: task_deposit_session_002

    이후 MA는 자기 내부 세션 ID로 글로벌 세션을 찾을 수 있습니다.
    """
    return service.register_agent_session(request)


# ============ Agent 세션 조회 ============


@router.get(
    "",
    response_model=AgentSessionGetResponse,
    summary="Agent 세션 조회",
    description="""
    MA 전용: Global 세션 키로 Agent 세션 키를 조회합니다.
    
    **허용 호출자**: MA만
    """,
)
async def get_agent_session(
    global_session_key: str = Query(..., description="Global 세션 키"),
    agent_id: str = Query(..., description="Agent ID"),
    service: SessionService = Depends(get_session_service),
    caller: APIKeyType = Depends(require_api_key([APIKeyType.MA])),
):
    """
    Agent 세션 조회 (MA 전용)

    MA가 글로벌 세션 키와 Agent ID로 자기 내부 세션 ID를 찾습니다.
    """
    return service.get_agent_session(global_session_key, agent_id)
