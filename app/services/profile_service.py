"""
Session Manager - Profile Service
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import (
    ProfileAttribute,
    ProfileGetResponse,
    BatchProfileRequest,
    BatchProfileResponse,
    BatchProfileError,
)


class ProfileService:
    """고객 프로파일 관리 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_customer_profile(
        self,
        session_id: str,
        user_id: str,
        attribute_keys: Optional[List[str]] = None,
    ) -> ProfileGetResponse:
        """고객 프로파일 조회"""
        # TODO: 실제 DB 조회 로직 구현
        # Mock 데이터 반환
        
        attributes = [
            ProfileAttribute(
                key="전세여부",
                value="Y",
                source_system="vertica_db",
                valid_from=None,
                valid_to=None,
            ),
            ProfileAttribute(
                key="선호채널",
                value="mobile",
                source_system="vertica_db",
                valid_from=None,
                valid_to=None,
            ),
        ]
        
        # attribute_keys 필터링
        if attribute_keys:
            attributes = [a for a in attributes if a.key in attribute_keys]
        
        return ProfileGetResponse(
            user_id=user_id,
            attributes=attributes,
            computed_at=datetime.utcnow(),
        )
    
    async def batch_upsert_profiles(
        self,
        request: BatchProfileRequest,
    ) -> BatchProfileResponse:
        """고객 프로파일 배치 업로드"""
        processed_count = 0
        failed_count = 0
        errors: List[BatchProfileError] = []
        
        for record in request.records:
            try:
                # TODO: 실제 DB Upsert 로직 구현
                # 현재는 Mock 처리
                processed_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(
                    BatchProfileError(
                        user_id=record.user_id,
                        error=str(e),
                    )
                )
        
        return BatchProfileResponse(
            batch_id=request.batch_id,
            accepted=failed_count == 0,
            processed_count=processed_count,
            failed_count=failed_count,
            errors=errors if errors else None,
        )
