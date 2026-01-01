"""
Session Manager - MA Profile API (v4.0)
MA → SM 고객 프로파일 조회
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_profile_service, verify_ma_api_key
from app.schemas.ma import ProfileGetResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/ma/profiles", tags=["MA - Customer Profile"])


@router.get(
    "/{user_id}",
    response_model=ProfileGetResponse,
    summary="고객 프로파일 조회",
    description="""
    MA가 고객 프로파일을 조회합니다.
    
    - Start 요청 시 customer_profile에 포함할 데이터
    - attribute_keys로 특정 속성만 필터링 가능
    """
)
def get_customer_profile(
    user_id: str,
    attribute_keys: list[str] | None = Query(None, description="조회할 속성 키 목록"),
    service: ProfileService = Depends(get_profile_service),
    api_key: str = Depends(verify_ma_api_key),
):
    return service.get_customer_profile(user_id, attribute_keys)
