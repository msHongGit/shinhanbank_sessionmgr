"""
Session Manager - Mock Session Repository (v4.0 - Sync)
In-Memory Dict 기반 세션 저장소 (Singleton)
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.repositories.base import SessionRepositoryInterface


class MockSessionRepository(SessionRepositoryInterface):
    """Mock 세션 Repository (Singleton, Sync)"""

    _instance = None
    _sessions: dict[str, dict[str, Any]] = {}
    _local_mappings: dict[str, dict[str, Any]] = {}
    _id_counter = 1

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _generate_id(self, prefix: str) -> str:
        """ID 생성"""
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{uuid4().hex[:6]}"

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
        """세션 생성"""
        if global_session_key in self._sessions:
            return self._sessions[global_session_key]

        now = datetime.now(UTC)
        session: dict[str, Any] = {
            "session_id": self._id_counter,
            "global_session_key": global_session_key,
            "user_id": user_id,
            "channel": channel,
            "conversation_id": conversation_id,
            "context_id": context_id,
            "session_state": session_state,
            "task_queue_status": task_queue_status,
            "subagent_status": subagent_status,
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        if customer_profile is not None:
            session["customer_profile"] = json.dumps(customer_profile)

        self._sessions[global_session_key] = session
        self._id_counter += 1

        return session

    def get(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 조회"""
        return self._sessions.get(global_session_key)

    def update(self, global_session_key: str, **kwargs) -> bool:
        """세션 업데이트"""
        if global_session_key not in self._sessions:
            return False

        now = datetime.now(UTC)
        self._sessions[global_session_key].update(kwargs)
        self._sessions[global_session_key]["updated_at"] = now.isoformat()

        return True

    def delete(self, global_session_key: str) -> bool:
        """세션 삭제"""
        if global_session_key in self._sessions:
            del self._sessions[global_session_key]
            return True
        return False

    def set_local_mapping(self, global_session_key: str, agent_id: str, local_session_key: str, agent_type: str) -> str:
        """Global↔Local 세션 매핑 등록"""
        mapping_key = f"{global_session_key}:{agent_id}"
        mapping_id = self._generate_id("map")

        self._local_mappings[mapping_key] = {
            "mapping_id": mapping_id,
            "global_session_key": global_session_key,
            "agent_session_key": local_session_key,  # API 스키마에서 agent_session_key로 사용
            "agent_id": agent_id,
            "agent_type": agent_type,
            "created_at": datetime.now(UTC).isoformat(),
            "last_used_at": datetime.now(UTC).isoformat(),
        }

        return mapping_id

    def get_local_mapping(self, global_session_key: str, agent_id: str) -> dict[str, Any] | None:
        """Local 세션 매핑 조회"""
        mapping_key = f"{global_session_key}:{agent_id}"
        return self._local_mappings.get(mapping_key)
