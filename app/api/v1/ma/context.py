"""
Session Manager - MA Context API (v4.0)
MA → SM 대화 이력 관리
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_context_service, verify_ma_api_key
from app.schemas.ma import (
    ConversationHistoryResponse,
    ConversationTurnSaveRequest,
    ConversationTurnSaveResponse,
)
from app.services.context_service import ContextService

router = APIRouter(prefix="/ma/context", tags=["MA - Conversation History"])


@router.get(
    "/history",
    response_model=ConversationHistoryResponse,
    summary="대화 이력 조회",
    description="""
    MA가 대화 이력을 조회합니다.
    
    - Talk 요청 시 conversation_history에 포함할 데이터
    - context_id 또는 global_session_key로 조회
    """
)
def get_conversation_history(
    global_session_key: str = Query(..., description="Global 세션 키"),
    context_id: str | None = Query(None, description="Context ID (없으면 세션에서 조회)"),
    service: ContextService = Depends(get_context_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.get_conversation_history(global_session_key, context_id)


@router.post(
    "/turn",
    response_model=ConversationTurnSaveResponse,
    status_code=201,
    summary="대화 턴 저장",
    description="""
    MA가 대화 턴을 저장합니다.
    
    - 사용자 발화, 어시스턴트 응답 저장
    - 각 턴마다 호출
    """
)
def save_conversation_turn(
    request: ConversationTurnSaveRequest,
    service: ContextService = Depends(get_context_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.save_conversation_turn(request)
