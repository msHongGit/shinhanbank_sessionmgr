"""
Session Manager - Mock Profile Repository (v4.0 - Sync)
In-Memory Dict 기반 Profile 저장소 (Singleton)
"""

from datetime import UTC, datetime
from typing import Any

from app.repositories.base import ProfileRepositoryInterface


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
        """프로파일 조회 (속성 리스트 반환)"""
        return self._profiles.get(user_id, [])

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
