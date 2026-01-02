"""Session Manager - Redis Session Repository (Sync).

Redis 기반 세션 저장소.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings
from app.db.redis import RedisHelper, get_redis_client
from app.repositories.base import SessionRepositoryInterface


class RedisSessionRepository(SessionRepositoryInterface):
    """Redis 기반 세션 Repository (Sync)

    - session:{global_session_key} 형태의 Hash에 세션 정보를 저장
    - Global↔Local 세션 매핑은 session_map:{global_session_key}:{agent_id} Hash에 저장
    """

    def __init__(self) -> None:
        client = get_redis_client()
        self.helper = RedisHelper(client)

    def create(
        self,
        global_session_key: str,
        user_id: str,
        channel: str,
        conversation_id: str,
        context_id: str,
        session_state: str,
        task_queue_status: str,
        subagent_status: str,
        customer_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """세션 생성 (존재 시 기존 세션 반환)"""
        existing = self.helper.get_session(global_session_key)
        if existing:
            return existing

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=settings.SESSION_CACHE_TTL)

        session: dict[str, Any] = {
            "session_id": global_session_key,
            "global_session_key": global_session_key,
            "user_id": user_id,
            "channel": channel,
            "conversation_id": conversation_id,
            "context_id": context_id,
            "session_state": session_state,
            "task_queue_status": task_queue_status,
            "subagent_status": subagent_status,
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        if customer_profile is not None:
            # 세션에 개인화 프로파일 스냅샷 저장 (JSON 직렬화)
            session["customer_profile"] = json.dumps(customer_profile)

        self.helper.set_session(global_session_key, session, ttl=settings.SESSION_CACHE_TTL)

        return session

    def get(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 조회"""
        return self.helper.get_session(global_session_key)

    def update(self, global_session_key: str, **kwargs: Any) -> dict[str, Any]:
        """세션 업데이트 (부분 업데이트)"""
        now = datetime.now(UTC).isoformat()
        updates = {**kwargs, "updated_at": now}
        self.helper.update_session(global_session_key, updates)
        updated = self.helper.get_session(global_session_key) or {}
        return updated

    def delete(self, global_session_key: str) -> bool:
        """세션 삭제"""
        before = self.helper.get_session(global_session_key)
        self.helper.delete_session(global_session_key)
        after = self.helper.get_session(global_session_key)
        return before is not None and after is None

    # ============ Global↔Local Session Mapping ============

    def set_local_mapping(self, global_session_key: str, agent_id: str, local_session_key: str, agent_type: str) -> str:
        """Global↔Local 세션 매핑 등록"""
        return self.helper.set_session_mapping(
            global_session_key=global_session_key,
            agent_id=agent_id,
            local_session_key=local_session_key,
            agent_type=agent_type,
            ttl=settings.SESSION_MAP_TTL,
        )

    def get_local_mapping(self, global_session_key: str, agent_id: str) -> dict[str, Any] | None:
        """Local 세션 매핑 조회"""
        return self.helper.get_session_mapping(global_session_key, agent_id)

    # ============ 조회 유틸 ============

    def list_all_sessions(self) -> list[dict[str, Any]]:
        """모든 세션 조회 (Portal 목록용)"""
        return self.helper.get_all_sessions()
