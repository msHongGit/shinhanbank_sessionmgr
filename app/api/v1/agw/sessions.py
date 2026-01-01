"""
Session Manager - AGW API (v4.0)
Agent GW → SM
초기 세션 생성 (Client가 발급한 Global Key 전달)
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_session_service, verify_agw_api_key
from app.schemas.agw import SessionCreateRequest, SessionCreateResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/agw", tags=["AGW - Agent Gateway"])


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    status_code=201,
    summary="초기 세션 생성",
    description="""
    Agent GW가 초기 세션을 생성합니다.
    
    - Client가 발급한 Global Session Key를 전달받아 세션 생성
    - 기존 세션이 유효하면 기존 세션 정보 반환 (is_new=false)
    - 새 세션 생성 시 conversation_id, context_id 발급
    """
)
def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
    api_key: str = Depends(verify_agw_api_key),
):
    """
    초기 세션 생성 API
    
    - **global_session_key**: Client가 발급한 Global 세션 키
    - **user_id**: 사용자 ID
    - **channel**: 채널 (mobile, web, kiosk)
    - **request_id**: 요청 추적 ID (옵션)
    - **device_info**: 디바이스 정보 (옵션)
    """
    return service.create_session(request)

