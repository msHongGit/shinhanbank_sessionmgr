"""Session Manager - Redis Session Repository (Sync).

Redis 기반 세션 저장소.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import SESSION_CACHE_TTL, SESSION_MAP_TTL
from app.db.redis import RedisHelper, get_redis_client


class RedisSessionRepository:
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
        profile: dict[str, Any] | None = None,
        start_type: str | None = None,
    ) -> dict[str, Any]:
        """세션 생성 (존재 시 기존 세션 반환)"""
        existing = self.helper.get_session(global_session_key)
        if existing:
            return existing

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=SESSION_CACHE_TTL)

        session: dict[str, Any] = {
            "global_session_key": global_session_key,
            "user_id": user_id,
            "channel": channel,
            "conversation_id": conversation_id,
            "context_id": context_id,
            "session_state": session_state,
            "task_queue_status": task_queue_status,
            "subagent_status": subagent_status,
            "profile": json.dumps(profile or {}),
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        if start_type is not None:
            # AGW startType 등 세션 진입 유형 메타데이터로 저장
            session["start_type"] = start_type

        if customer_profile is not None:
            # 세션에 개인화 프로파일 스냅샷 저장 (JSON 직렬화)
            session["customer_profile"] = json.dumps(customer_profile)

        self.helper.set_session(global_session_key, session, ttl=SESSION_CACHE_TTL)

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

    def refresh_ttl(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 TTL 연장 및 만료 시각 갱신.

        세션이 존재하면 SESSION_CACHE_TTL 기준으로 expires_at을 다시 설정하고 Redis TTL도 연장한다.
        존재하지 않으면 None을 반환한다.
        """

        session = self.helper.get_session(global_session_key)
        if not session:
            return None

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=SESSION_CACHE_TTL)
        session["expires_at"] = expires_at.isoformat()
        self.helper.set_session(global_session_key, session, ttl=SESSION_CACHE_TTL)
        return session

    # ============ Global↔Local Session Mapping ============

    def set_local_mapping(self, global_session_key: str, agent_id: str, agent_session_key: str, agent_type: str) -> str:
        """Global↔Local 세션 매핑 등록"""
        return self.helper.set_session_mapping(
            global_session_key=global_session_key,
            agent_id=agent_id,
            agent_session_key=agent_session_key,
            agent_type=agent_type,
            ttl=SESSION_MAP_TTL,
        )

    def get_local_mapping(self, global_session_key: str, agent_id: str) -> dict[str, Any] | None:
        """Local 세션 매핑 조회"""
        return self.helper.get_session_mapping(global_session_key, agent_id)

    # ============ 조회 유틸 ============

    def list_all_sessions(self) -> list[dict[str, Any]]:
        """모든 세션 조회 (Portal 목록용)"""
        return self.helper.get_all_sessions()
