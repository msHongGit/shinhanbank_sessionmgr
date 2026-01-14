"""
Session Manager - Mock Context Repository (v4.0 - Sync)
In-Memory Dict 기반 Context 저장소 (Singleton)
"""

from datetime import UTC, datetime
from typing import Any


class MockContextRepository:
    """Mock Context Repository (Singleton, Sync)"""

    _instance = None
    _contexts: dict[str, dict[str, Any]] = {}
    _turns: dict[str, list[dict[str, Any]]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def create(self, context_id: str, global_session_key: str, user_id: str) -> dict[str, Any]:
        """Context 생성"""
        now = datetime.now(UTC)
        context = {
            "context_id": context_id,
            "global_session_key": global_session_key,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        self._contexts[context_id] = context
        self._turns[context_id] = []

        return context

    def get(self, context_id: str) -> dict[str, Any] | None:
        """Context 조회"""
        return self._contexts.get(context_id)

    def add_turn(self, context_id: str, turn_data: dict[str, Any]) -> None:
        """대화 턴 추가"""
        if context_id not in self._turns:
            self._turns[context_id] = []

        self._turns[context_id].append(turn_data)

        # Context updated_at 업데이트
        if context_id in self._contexts:
            self._contexts[context_id]["updated_at"] = datetime.now(UTC).isoformat()

    def get_turns(self, context_id: str) -> list[dict[str, Any]]:
        """대화 턴 목록 조회"""
        return self._turns.get(context_id, [])

    def delete(self, context_id: str) -> int:
        """Context 삭제 (삭제된 턴 수 반환)"""
        deleted_count = 0

        if context_id in self._contexts:
            del self._contexts[context_id]

        if context_id in self._turns:
            deleted_count = len(self._turns[context_id])
            del self._turns[context_id]

        return deleted_count
