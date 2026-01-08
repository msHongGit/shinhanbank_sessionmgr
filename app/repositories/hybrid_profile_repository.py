"""
Session Manager - Hybrid Profile Repository
Redis 캐시 + MariaDB 영구 저장소
"""

from datetime import date
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.repositories.mariadb_profile_repository import MariaDBProfileRepository
from app.repositories.redis_profile_repository import RedisProfileRepository
from app.schemas.common import CustomerProfile


class HybridProfileRepository:
    """Profile repository with Redis cache + MariaDB persistence.

    Cache-aside pattern:
    1. Try Redis first (fast)
    2. On cache miss → Query MariaDB
    3. Update Redis in background
    """

    def __init__(self, db_session: Session):
        self._redis = RedisProfileRepository()
        self._mariadb = MariaDBProfileRepository(db_session)

    def get_profile(
        self,
        user_id: str,
        context_id: str | None = None,
        as_of_date: date | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> CustomerProfile | None:
        """Get profile with cache-aside pattern.

        Args:
            user_id: User identifier
            context_id: Optional context filter
            as_of_date: Optional date for temporal filtering
            background_tasks: Optional background task queue

        Returns:
            CustomerProfile or None if not found
        """
        # 1. Try Redis cache first (only if no filters)
        if not context_id and not as_of_date:
            cached = self._redis.get_profile(user_id)
            if cached:
                return cached

        # 2. Cache miss → Query MariaDB
        profile = self._mariadb.get_profile_by_user(user_id=user_id, context_id=context_id, as_of_date=as_of_date)

        if not profile:
            return None

        # 3. Update cache in background (only if no filters)
        if background_tasks and not context_id and not as_of_date:
            background_tasks.add_task(self._redis.set_profile, profile)

        return profile

    def get_profile_dict(
        self,
        user_id: str,
        context_id: str | None = None,
        as_of_date: date | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Get profile as simple dict.

        Args:
            user_id: User identifier
            context_id: Optional context filter
            as_of_date: Optional date for temporal filtering
            background_tasks: Optional background task queue

        Returns:
            Profile dict (empty if not found)
        """
        # 1. Try Redis cache first (only if no filters)
        if not context_id and not as_of_date:
            cached_dict = self._redis.get_profile_dict(user_id)
            if cached_dict:
                return cached_dict

        # 2. Cache miss → Query MariaDB
        profile = self._mariadb.get_profile_by_user(user_id=user_id, context_id=context_id, as_of_date=as_of_date)

        if not profile:
            return {}

        profile_dict = profile.to_dict()

        # 3. Update cache in background (only if no filters)
        if background_tasks and not context_id and not as_of_date:
            background_tasks.add_task(self._redis.set_profile_dict, user_id, profile_dict)

        return profile_dict

    def invalidate_cache(self, user_id: str) -> None:
        """Invalidate profile cache.

        Args:
            user_id: User identifier
        """
        self._redis.delete_profile(user_id)
