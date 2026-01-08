"""
Session Manager - Profile Service (v4.0 - Sync)
고객 프로파일 관리 (Sync 방식)
"""

from datetime import UTC, datetime

from app.repositories.base import ProfileRepositoryInterface
from app.repositories.mock import MockProfileRepository
from app.schemas.common import CustomerProfile, ProfileAttribute, ProfileGetResponse


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


def get_profile_service() -> ProfileService:
    """ProfileService 인스턴스 반환 (DI)"""
    return ProfileService(profile_repo=MockProfileRepository())
