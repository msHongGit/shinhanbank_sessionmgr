"""Session Manager - Redis Profile Repository.

사용자 프로파일 캐시 저장소 (Redis).

ma_session 도메인 모델 대신 app.schemas.common.CustomerProfile을 사용한다.
"""

import json
from typing import Any

from app.db.redis import get_redis_client
from app.schemas.common import CustomerProfile

PROFILE_KEY_PATTERN = "profile:{user_id}"
PROFILE_TTL = 3600  # 1 hour cache


class RedisProfileRepository:
    """Profile repository with Redis caching."""

    def __init__(self):
        self._redis = get_redis_client()

    def get_profile(self, user_id: str) -> CustomerProfile | None:
        """Get cached profile from Redis.

        Args:
            user_id: User identifier

        Returns:
            CustomerProfile or None if cache miss
        """
        key = PROFILE_KEY_PATTERN.format(user_id=user_id)
        data = self._redis.get(key)

        if not data:
            return None

        try:
            profile_dict = json.loads(data)
            return CustomerProfile(**profile_dict)
        except Exception:
            # Invalid cache data
            return None

    def set_profile(self, profile: CustomerProfile) -> None:
        """Cache profile in Redis.

        Args:
            profile: CustomerProfile to cache
        """
        key = PROFILE_KEY_PATTERN.format(user_id=profile.user_id)
        try:
            profile_json = json.dumps(profile.model_dump(), default=str)
            self._redis.setex(key, PROFILE_TTL, profile_json)
        except Exception:  # noqa: S110
            # Ignore cache errors by design
            pass

    def delete_profile(self, user_id: str) -> None:
        """Invalidate profile cache.

        Args:
            user_id: User identifier
        """
        key = PROFILE_KEY_PATTERN.format(user_id=user_id)
        self._redis.delete(key)

    def get_profile_dict(self, user_id: str) -> dict[str, Any] | None:
        """Get cached profile as simple dict.

        Args:
            user_id: User identifier

        Returns:
            Profile dict or None if cache miss
        """
        profile = self.get_profile(user_id)
        if not profile:
            return None

        return profile.to_dict()

    def set_profile_dict(self, user_id: str, profile_dict: dict[str, Any]) -> None:
        """Cache profile dict directly.

        Args:
            user_id: User identifier
            profile_dict: Profile dictionary
        """
        key = PROFILE_KEY_PATTERN.format(user_id=user_id)
        try:
            profile_json = json.dumps(profile_dict, default=str)
            self._redis.setex(key, PROFILE_TTL, profile_json)
        except Exception:  # noqa: S110
            # Ignore cache errors by design
            pass
