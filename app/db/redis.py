"""
Session Manager - Redis Connection (Sync)
v3.0: 모든 연동 Sync 방식
"""

import json
from typing import Any

import redis

_redis_client: redis.Redis | None = None


def init_redis() -> None:
    """Initialize Redis connection (Sync)"""
    from app.config import REDIS_MAX_CONNECTIONS, REDIS_URL

    global _redis_client
    _redis_client = redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=REDIS_MAX_CONNECTIONS,
    )
    try:
        _redis_client.ping()
        print("✅ Redis connected (Sync)")
    except Exception as e:
        print(f"⚠️ Redis connection warning: {e}")
        # Continue anyway - connection will be retried on first use


def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        print("❌ Redis disconnected")


def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    global _redis_client
    if not _redis_client:
        init_redis()
    return _redis_client


class RedisHelper:
    """Redis Helper for Session Manager"""

    def __init__(self, client: redis.Redis):
        self.client = client

    # ============ Session Cache ============

    def get_session(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 조회"""
        data = self.client.hgetall(f"session:{global_session_key}")
        return data if data else None

    def set_session(self, global_session_key: str, data: dict[str, Any], ttl: int = None) -> None:
        """세션 저장"""
        from app.config import SESSION_CACHE_TTL

        key = f"session:{global_session_key}"
        self.client.hset(key, mapping=data)
        self.client.expire(key, ttl or SESSION_CACHE_TTL)

    def delete_session(self, global_session_key: str) -> None:
        """세션 삭제"""
        self.client.delete(f"session:{global_session_key}")

    def update_session(self, global_session_key: str, updates: dict[str, Any]) -> None:
        """세션 업데이트"""
        key = f"session:{global_session_key}"
        if not self.client.exists(key):
            return

        clean_updates = {k: v for k, v in updates.items() if v is not None}
        if not clean_updates:
            return

        self.client.hset(key, mapping=clean_updates)

    def get_all_sessions(self, pattern: str = "session:*") -> list[dict[str, Any]]:
        """모든 세션 조회"""
        keys = self.client.keys(pattern)
        sessions = []
        for key in keys:
            data = self.client.hgetall(key)
            if data:
                sessions.append(data)
        return sessions

    # ============ Turns (대화 턴 이력) ============

    def get_context_turns(self, global_session_key: str) -> list[dict[str, Any]]:
        """세션의 대화 턴 조회"""
        turns_json = self.client.lrange(f"turns:{global_session_key}", 0, -1)
        return [json.loads(t) for t in turns_json]

    def add_context_turn(self, global_session_key: str, turn: dict[str, Any]) -> None:
        """세션의 대화 턴 추가"""
        self.client.rpush(f"turns:{global_session_key}", json.dumps(turn))

    def delete_context_turns(self, global_session_key: str) -> int:
        """세션의 대화 턴 삭제"""
        count = self.client.llen(f"turns:{global_session_key}")
        self.client.delete(f"turns:{global_session_key}")
        return count
