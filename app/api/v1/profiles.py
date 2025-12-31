"""
Session Manager - Profile API Endpoints
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List

from app.schemas.profile import (
    ProfileGetResponse,
    BatchProfileRequest,
    BatchProfileResponse,
)
from app.services.profile_service import ProfileService
from app.api.deps import get_profile_service, verify_api_key

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get(
    "/{user_id}",
    response_model=ProfileGetResponse,
    summary="고객 프로파일 조회",
    description="고객 프로파일을 조회합니다. (MA-SM-07)"
)
async def get_customer_profile(
    user_id: str,
    session_id: str = Query(..., description="세션 ID"),
    attribute_keys: Optional[List[str]] = Query(None, description="조회할 속성 키 목록"),
    service: ProfileService = Depends(get_profile_service),
    api_key: str = Depends(verify_api_key),
):
    """
    고객 프로파일 조회 API
    
    - **user_id**: 사용자 ID
    - **session_id**: 세션 ID
    - **attribute_keys**: 조회할 속성 키 목록 (미지정 시 전체)
    """
    return await service.get_customer_profile(session_id, user_id, attribute_keys)


@router.post(
    "/batch",
    response_model=BatchProfileResponse,
    summary="고객 프로파일 배치 업로드",
    description="고객 프로파일을 배치로 업로드합니다. (VDB-SM-01)"
)
async def batch_upsert_profiles(
    request: BatchProfileRequest,
    service: ProfileService = Depends(get_profile_service),
    api_key: str = Depends(verify_api_key),
):
    """
    고객 프로파일 배치 업로드 API
    
    - **batch_id**: 배치 ID
    - **source_system**: 소스 시스템
    - **records**: 프로파일 레코드 목록
    """
    return await service.batch_upsert_profiles(request)
