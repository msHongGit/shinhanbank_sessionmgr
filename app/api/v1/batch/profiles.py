"""
Session Manager - Batch API (v4.0)
VDB → SM 배치 처리
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_profile_service, verify_vdb_api_key
from app.schemas.batch import BatchProfileRequest, BatchProfileResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/batch", tags=["Batch - VDB"])


@router.post(
    "/profiles",
    response_model=BatchProfileResponse,
    summary="프로파일 배치 업로드",
    description="""
    VDB에서 고객 프로파일을 배치로 업로드합니다.
    
    - 다수의 고객 프로파일을 한 번에 Upsert
    - 처리 결과 (성공/실패 건수) 반환
    """
)
def batch_upsert_profiles(
    request: BatchProfileRequest,
    service: ProfileService = Depends(get_profile_service),
    api_key: str = Depends(verify_vdb_api_key),
):
    return service.batch_upsert_profiles(request)
