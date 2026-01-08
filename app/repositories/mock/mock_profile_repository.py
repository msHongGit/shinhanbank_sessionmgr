"""Session Manager - Mock Profile Repository (v4.0 - Sync).

In-Memory Dict 기반 Profile 저장소 (Singleton).

ma_session은 참고용 도메인 모델이므로,
여기서는 app.schemas.common의 CustomerProfile을 사용한다.
"""

from datetime import UTC, datetime
from typing import Any

from app.repositories.base import ProfileRepositoryInterface
from app.schemas.common import CustomerProfile, ProfileAttribute


class MockProfileRepository(ProfileRepositoryInterface):
    """Mock Profile Repository (Singleton, Sync)"""

    _instance = None
    _profiles: dict[str, list[dict[str, Any]]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_mock_data()
        return cls._instance

    def _init_mock_data(self):
        """Mock 데이터 초기화"""
        self._profiles = {
            "user_vip_001": [
                {
                    "user_id": "user_vip_001",
                    "attribute_key": "segment",
                    "attribute_value": "VIP",
                    "source_system": "CRM",
                    "valid_from": "2025-01-01",
                    "valid_to": None,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                {
                    "user_id": "user_vip_001",
                    "attribute_key": "preferred_language",
                    "attribute_value": "ko",
                    "source_system": "CRM",
                    "valid_from": "2025-01-01",
                    "valid_to": None,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            ]
        }

    def get(self, user_id: str) -> list[dict[str, Any]]:
        """프로파일 조회 (원시 속성 리스트 반환).

        ProfileService 등에서 직접 속성 dict를 가공할 때 사용한다.
        """
        return self._profiles.get(user_id, [])

    def get_profile(self, user_id: str, context_id: str | None = None, **kwargs) -> CustomerProfile | None:
        """프로파일 조회 (schemas.common.CustomerProfile 객체 반환).

        SessionService 등에서 고객 프로파일 스냅샷이 필요할 때 사용한다.
        """
        attributes_data = self._profiles.get(user_id, [])
        if not attributes_data:
            return None

        # 속성 리스트를 ProfileAttribute로 변환
        attributes: list[ProfileAttribute] = []
        segment: str | None = None

        for attr in attributes_data:
            pa = ProfileAttribute(
                key=attr["attribute_key"],
                value=attr["attribute_value"],
                source_system=attr.get("source_system", "MOCK"),
                valid_from=attr.get("valid_from"),
                valid_to=attr.get("valid_to"),
            )
            attributes.append(pa)

            if pa.key == "segment":
                segment = pa.value

        return CustomerProfile(
            user_id=user_id,
            attributes=attributes,
            segment=segment,
            preferences={"source": "mock"},
        )

    def batch_upsert(self, profiles: list[dict[str, Any]]) -> int:
        """프로파일 배치 업데이트"""
        now = datetime.now(UTC).isoformat()
        processed = 0

        for profile in profiles:
            user_id = profile["user_id"]

            if user_id not in self._profiles:
                self._profiles[user_id] = []

            # 기존 속성 찾기
            existing_idx = None
            for idx, p in enumerate(self._profiles[user_id]):
                if p["attribute_key"] == profile["attribute_key"]:
                    existing_idx = idx
                    break

            # Upsert
            profile_data = {
                **profile,
                "updated_at": now,
                "created_at": profile.get("created_at", now),
            }

            if existing_idx is not None:
                self._profiles[user_id][existing_idx] = profile_data
            else:
                self._profiles[user_id].append(profile_data)

            processed += 1

        return processed
