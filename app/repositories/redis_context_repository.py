"""
Session Manager - Redis Context Repository (Sync)
Redis 기반 Context 저장소
"""

from datetime import UTC, datetime
from typing import Any

from app.db.redis import RedisHelper, get_redis_client
from app.repositories.base import ContextRepositoryInterface


class RedisContextRepository(ContextRepositoryInterface):
    """Redis 기반 Context Repository (Sync)

    - context:{context_id} Hash에 Context 메타데이터 저장
    - context_turns:{context_id} List에 턴 이력 저장
    """

    def __init__(self) -> None:
        client = get_redis_client()
        self.helper = RedisHelper(client)

    def create(self, context_id: str, global_session_key: str, user_id: str) -> dict[str, Any]:
        """Context 생성"""
        now = datetime.now(UTC)
        context: dict[str, Any] = {
            "context_id": context_id,
            "global_session_key": global_session_key,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "last_updated_at": now.isoformat(),
        }
        self.helper.set_context(context_id, context)
        return context

    def get(self, context_id: str) -> dict[str, Any] | None:
        """Context 조회"""
        return self.helper.get_context(context_id)

    def add_turn(self, context_id: str, turn_data: dict[str, Any]) -> None:
        """대화 턴 추가"""
        self.helper.add_context_turn(context_id, turn_data)

        context = self.helper.get_context(context_id)
        if context:
            context["last_updated_at"] = datetime.now(UTC).isoformat()
            self.helper.set_context(context_id, context)

    def get_turns(self, context_id: str) -> list[dict[str, Any]]:
        """대화 턴 목록 조회"""
        return self.helper.get_context_turns(context_id)

    def delete(self, context_id: str) -> int:
        """Context 삭제 (삭제된 턴 수 반환)"""
        turns = self.helper.get_context_turns(context_id)
        deleted_turns = self.helper.delete_context_turns(context_id)
        self.helper.delete_context(context_id)
        return deleted_turns if deleted_turns is not None else len(turns)
