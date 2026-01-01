"""
Session Manager - Profile Service (v4.0 - Sync)
고객 프로파일 관리 (Sync 방식)
"""
from datetime import UTC, datetime

from app.repositories.base import ProfileRepositoryInterface
from app.repositories.mock import MockProfileRepository
from app.schemas import CustomerProfile, ProfileAttribute
from app.schemas.batch import BatchProfileError, BatchProfileRequest, BatchProfileResponse
from app.schemas.ma import ProfileGetResponse


class ProfileService:
    """고객 프로파일 관리 서비스 (Sync)"""

    def __init__(self, profile_repo: ProfileRepositoryInterface | None = None):
        self.profile_repo = profile_repo or MockProfileRepository()

    # ============ MA API ============

    def get_customer_profile(
        self,
        user_id: str,
        attribute_keys: list[str] | None = None,
    ) -> ProfileGetResponse:
        """고객 프로파일 조회 (MA → SM)"""
        profile_data = self.profile_repo.get(user_id)

        attributes = []
        for p in profile_data:
            attr = ProfileAttribute(
                key=p.get("attribute_key", ""),
                value=p.get("attribute_value", ""),
                source_system=p.get("source_system"),
                valid_from=p.get("valid_from"),
                valid_to=p.get("valid_to"),
            )
            attributes.append(attr)

        if attribute_keys:
            attributes = [a for a in attributes if a.key in attribute_keys]

        segment = None
        for attr in attributes:
            if attr.key == "segment":
                segment = attr.value
                break

        profile = CustomerProfile(
            user_id=user_id,
            attributes=attributes,
            segment=segment,
            preferences={"language": "ko"},
        )

        return ProfileGetResponse(
            user_id=user_id,
            profile=profile,
            computed_at=datetime.now(UTC),
        )

    # ============ Batch API (VDB) ============

    def batch_upsert_profiles(self, request: BatchProfileRequest) -> BatchProfileResponse:
        """고객 프로파일 배치 업로드 (VDB → SM)"""
        processed_count = 0
        failed_count = 0
        errors: list[BatchProfileError] = []

        profiles_to_upsert = []
        for record in request.records:
            for attr in record.attributes:
                profiles_to_upsert.append({
                    "user_id": record.user_id,
                    "attribute_key": attr.key,
                    "attribute_value": attr.value,
                    "source_system": attr.source_system or "VDB",
                })

        try:
            processed_count = self.profile_repo.batch_upsert(profiles_to_upsert)
        except Exception as e:
            failed_count = len(profiles_to_upsert)
            errors.append(BatchProfileError(user_id="batch", error=str(e)))

        return BatchProfileResponse(
            batch_id=request.batch_id,
            accepted=failed_count == 0,
            processed_count=processed_count,
            failed_count=failed_count,
            errors=errors if errors else None,
        )


def get_profile_service() -> ProfileService:
    """ProfileService 인스턴스 반환 (DI)"""
    return ProfileService(profile_repo=MockProfileRepository())
