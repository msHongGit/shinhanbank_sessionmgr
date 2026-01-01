"""
Session Manager - Redis Connection (Sync)
v3.0: 모든 연동 Sync 방식
"""
import json
from typing import Any

import redis

from app.config import settings

_redis_client: redis.Redis | None = None


def init_redis() -> None:
    """Initialize Redis connection (Sync)"""
    global _redis_client
    _redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
    _redis_client.ping()
    print("✅ Redis connected (Sync)")


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
        key = f"session:{global_session_key}"
        self.client.hset(key, mapping=data)
        self.client.expire(key, ttl or settings.SESSION_CACHE_TTL)

    def delete_session(self, global_session_key: str) -> None:
        """세션 삭제"""
        self.client.delete(f"session:{global_session_key}")

    def update_session(self, global_session_key: str, updates: dict[str, Any]) -> None:
        """세션 업데이트"""
        key = f"session:{global_session_key}"
        if self.client.exists(key):
            self.client.hset(key, mapping=updates)

    def get_all_sessions(self, pattern: str = "session:*") -> list[dict[str, Any]]:
        """모든 세션 조회"""
        keys = self.client.keys(pattern)
        sessions = []
        for key in keys:
            data = self.client.hgetall(key)
            if data:
                sessions.append(data)
        return sessions

    # ============ Global↔Local Session Mapping ============

    def set_session_mapping(
        self,
        global_session_key: str,
        agent_id: str,
        local_session_key: str,
        agent_type: str,
        ttl: int = None
    ) -> str:
        """Global↔Local 세션 매핑 저장"""
        mapping_key = f"session_map:{global_session_key}:{agent_id}"
        mapping_data = {
            "global_session_key": global_session_key,
            "local_session_key": local_session_key,
            "agent_id": agent_id,
            "agent_type": agent_type,
        }
        self.client.hset(mapping_key, mapping=mapping_data)
        self.client.expire(mapping_key, ttl or settings.SESSION_MAP_TTL)
        return mapping_key

    def get_session_mapping(self, global_session_key: str, agent_id: str) -> dict[str, Any] | None:
        """Global↔Local 세션 매핑 조회"""
        mapping_key = f"session_map:{global_session_key}:{agent_id}"
        data = self.client.hgetall(mapping_key)
        return data if data else None

    def get_local_session(self, global_session_key: str, agent_id: str) -> str | None:
        """Local 세션 키 조회"""
        mapping = self.get_session_mapping(global_session_key, agent_id)
        return mapping.get("local_session_key") if mapping else None

    def delete_session_mapping(self, global_session_key: str, agent_id: str) -> None:
        """세션 매핑 삭제"""
        mapping_key = f"session_map:{global_session_key}:{agent_id}"
        self.client.delete(mapping_key)

    def delete_all_mappings_for_session(self, global_session_key: str) -> int:
        """세션의 모든 매핑 삭제"""
        pattern = f"session_map:{global_session_key}:*"
        keys = self.client.keys(pattern)
        if keys:
            return self.client.delete(*keys)
        return 0

    # ============ Task Queue ============

    def enqueue_task(self, global_session_key: str, task_data: dict[str, Any], priority: int) -> None:
        """Task 적재"""
        queue_key = f"task_queue:{global_session_key}"
        self.client.zadd(queue_key, {json.dumps(task_data): priority})

    def dequeue_task(self, global_session_key: str) -> dict[str, Any] | None:
        """Task 꺼내기"""
        queue_key = f"task_queue:{global_session_key}"
        tasks = self.client.zrange(queue_key, 0, 0)
        if tasks:
            self.client.zrem(queue_key, tasks[0])
            return json.loads(tasks[0])
        return None

    def get_task_queue_count(self, global_session_key: str) -> int:
        """Task Queue 개수"""
        return self.client.zcard(f"task_queue:{global_session_key}")

    def clear_task_queue(self, global_session_key: str) -> None:
        """Task Queue 비우기"""
        self.client.delete(f"task_queue:{global_session_key}")

    # ============ Context (대화 이력) ============

    def get_context(self, context_id: str) -> dict[str, Any] | None:
        """Context 조회"""
        data = self.client.hgetall(f"context:{context_id}")
        return data if data else None

    def set_context(self, context_id: str, data: dict[str, Any]) -> None:
        """Context 저장"""
        self.client.hset(f"context:{context_id}", mapping=data)

    def delete_context(self, context_id: str) -> bool:
        """Context 삭제"""
        return self.client.delete(f"context:{context_id}") > 0

    def get_context_turns(self, context_id: str) -> list[dict[str, Any]]:
        """Context 대화 턴 조회"""
        turns_json = self.client.lrange(f"context_turns:{context_id}", 0, -1)
        return [json.loads(t) for t in turns_json]

    def add_context_turn(self, context_id: str, turn: dict[str, Any]) -> None:
        """Context 대화 턴 추가"""
        self.client.rpush(f"context_turns:{context_id}", json.dumps(turn))

    def delete_context_turns(self, context_id: str) -> int:
        """Context 대화 턴 삭제"""
        count = self.client.llen(f"context_turns:{context_id}")
        self.client.delete(f"context_turns:{context_id}")
        return count
