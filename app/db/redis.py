"""
Session Manager - Redis Connection (Async)
v4.0: 모든 연동 Async 방식
"""

import json
from decimal import Decimal
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

_redis_client: redis.Redis | None = None


def _json_serializer(obj: Any) -> Any:
    """JSON 직렬화 헬퍼 (Decimal 타입 지원)"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


async def init_redis() -> None:
    """Initialize Redis connection (Async)"""
    # 기본: 단일 Redis 인스턴스 (REDIS_URL 기반)
    from app.config import REDIS_MAX_CONNECTIONS, REDIS_URL

    # global _redis_client
    # _redis_client = redis.from_url(
    #     REDIS_URL,
    #     encoding="utf-8",
    #     decode_responses=True,
    #     max_connections=REDIS_MAX_CONNECTIONS,
    # )

    # On-Prem Sentinel 환경에서 사용할 경우, 위 블록을 주석 처리하고
    # 아래 예시 블록의 주석을 해제해 Sentinel 기반으로 연결할 수 있습니다.
    #
    from redis.asyncio.sentinel import Sentinel
    from app.config import (
        REDIS_SENTINEL_NODES,         # [(host, port), ...]
        REDIS_SENTINEL_MASTER_NAME,   # 예: "mymaster"
        REDIS_USERNAME,
        REDIS_PASSWORD,
        REDIS_DB,                     # 예: 6
    )
    
    sentinel = Sentinel(
        REDIS_SENTINEL_NODES,
        sentinel_kwargs={},
        decode_responses=True,
    )
    
    global _redis_client
    _redis_client = sentinel.master_for(
        REDIS_SENTINEL_MASTER_NAME,
        db=REDIS_DB,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        encoding="utf-8",
        decode_responses=True,
        max_connections=REDIS_MAX_CONNECTIONS,
    )
    try:
        await _redis_client.ping()
        print("✅ Redis connected (Async)")
    except RedisError as e:
        print(f"⚠️ Redis connection warning: {e}")
        # Continue anyway - connection will be retried on first use


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        print("❌ Redis disconnected")


def get_redis_client() -> redis.Redis:
    """Get Redis client instance

    테스트 환경에서는 매 테스트마다 새로 생성하되, 연결 풀을 재사용하여 성능 향상.
    프로덕션 환경에서는 전역 클라이언트를 사용.
    """
    global _redis_client
    import os

    # 프로덕션 환경에서는 전역 클라이언트 사용
    if not os.getenv("PYTEST_CURRENT_TEST"):
        if not _redis_client:
            raise RuntimeError("Redis client not initialized. Call init_redis() first.")
        return _redis_client

    # 테스트 환경에서는 매번 새로 생성 (이벤트 루프 충돌 방지)
    # 하지만 연결 풀은 내부적으로 재사용됨
    from app.config import REDIS_MAX_CONNECTIONS, REDIS_URL

    return redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=REDIS_MAX_CONNECTIONS,
    )


class RedisHelper:
    """Redis Helper for Session Manager (Async)"""

    def __init__(self, client: redis.Redis):
        self.client = client

    # ============ Session Cache ============

    async def get_session(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 조회"""
        data = await self.client.hgetall(f"session:{global_session_key}")
        return data if data else None

    async def set_session(self, global_session_key: str, data: dict[str, Any], ttl: int = None) -> None:
        """세션 저장"""
        from app.config import SESSION_CACHE_TTL

        key = f"session:{global_session_key}"
        await self.client.hset(key, mapping=data)
        await self.client.expire(key, ttl or SESSION_CACHE_TTL)

    async def delete_session(self, global_session_key: str) -> None:
        """세션 삭제"""
        await self.client.delete(f"session:{global_session_key}")

    async def update_session(self, global_session_key: str, updates: dict[str, Any]) -> None:
        """세션 업데이트"""
        key = f"session:{global_session_key}"
        exists = await self.client.exists(key)
        if not exists:
            return

        clean_updates = {k: v for k, v in updates.items() if v is not None}
        if not clean_updates:
            return

        await self.client.hset(key, mapping=clean_updates)

    async def get_all_sessions(self, pattern: str = "session:*") -> list[dict[str, Any]]:
        """모든 세션 조회"""
        keys = await self.client.keys(pattern)
        sessions = []
        for key in keys:
            data = await self.client.hgetall(key)
            if data:
                sessions.append(data)
        return sessions

    # ============ Turns (대화 턴 이력) ============

    async def get_context_turns(self, global_session_key: str) -> list[dict[str, Any]]:
        """세션의 대화 턴 조회"""
        turns_json = await self.client.lrange(f"turns:{global_session_key}", 0, -1)
        return [json.loads(t) for t in turns_json]

    async def add_context_turn(self, global_session_key: str, turn: dict[str, Any]) -> None:
        """세션의 대화 턴 추가 (세션과 동일한 TTL 설정)"""
        from app.config import SESSION_CACHE_TTL

        key = f"turns:{global_session_key}"
        await self.client.rpush(key, json.dumps(turn))
        # 세션과 동일한 TTL 설정
        await self.client.expire(key, SESSION_CACHE_TTL)

    async def delete_context_turns(self, global_session_key: str) -> int:
        """세션의 대화 턴 삭제"""
        count = await self.client.llen(f"turns:{global_session_key}")
        await self.client.delete(f"turns:{global_session_key}")
        return count

    # ============ JTI Mapping ============

    async def set_jti_mapping(self, jti: str, global_session_key: str, ttl: int = 300) -> None:
        """jti -> global_session_key 매핑 저장

        Args:
            jti: JWT ID (UUID)
            global_session_key: Global 세션 키
            ttl: TTL (초 단위, 기본값 300초)
        """
        await self.client.setex(f"jti:{jti}", ttl, global_session_key)

    async def get_global_session_key_by_jti(self, jti: str) -> str | None:
        """jti로 global_session_key 조회

        Args:
            jti: JWT ID (UUID)

        Returns:
            global_session_key 또는 None
        """
        result = await self.client.get(f"jti:{jti}")
        if result:
            return result if isinstance(result, str) else result.decode()
        return None

    # ============ 실시간 프로파일 ============

    async def get_realtime_profile(self, user_id: str) -> dict[str, Any] | None:
        """실시간 프로파일 조회

        Args:
            user_id: 사용자 ID (10자리 숫자, 예: "0616001905")

        Returns:
            실시간 프로파일 데이터 (dict) 또는 None
        """
        data = await self.client.get(f"profile:realtime:{user_id}")
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_realtime_profile(self, user_id: str, profile_data: dict[str, Any], ttl: int | None = None) -> None:
        """실시간 프로파일 저장 (세션과 동일한 TTL 설정)

        Args:
            user_id: 사용자 ID (cusno 또는 global_session_key)
            profile_data: 실시간 프로파일 데이터 (dict, redis_data.md 구조 그대로 저장)
            ttl: TTL (초 단위, None이면 SESSION_CACHE_TTL 사용)
        """
        from app.config import SESSION_CACHE_TTL

        key = f"profile:realtime:{user_id}"
        await self.client.set(key, json.dumps(profile_data, ensure_ascii=False, default=_json_serializer))
        await self.client.expire(key, ttl or SESSION_CACHE_TTL)

    # ============ 배치 프로파일 ============

    async def get_batch_profile(self, user_id: str) -> dict[str, Any] | None:
        """배치 프로파일 조회 (일별+월별)

        Args:
            user_id: 사용자 ID (10자리 숫자, 예: "0616001905")

        Returns:
            배치 프로파일 데이터 (dict) 또는 None
            {
                "daily": {...},    # IFC_CUS_DD_SMRY_TOT 테이블 데이터
                "monthly": {...}   # IFC_CUS_MMBY_SMRY_TOT 테이블 데이터
            }
        """
        data = await self.client.get(f"profile:batch:{user_id}")
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def set_batch_profile(self, user_id: str, profile_data: dict[str, Any], ttl: int | None = None) -> None:
        """배치 프로파일 저장 (세션과 동일한 TTL 설정)

        Args:
            user_id: 사용자 ID (cusno)
            profile_data: 배치 프로파일 데이터 (dict)
            {
                "daily": {...},    # IFC_CUS_DD_SMRY_TOT 테이블 데이터
                "monthly": {...}   # IFC_CUS_MMBY_SMRY_TOT 테이블 데이터
            }
            ttl: TTL (초 단위, None이면 SESSION_CACHE_TTL 사용)
        """
        from app.config import SESSION_CACHE_TTL

        key = f"profile:batch:{user_id}"
        await self.client.set(key, json.dumps(profile_data, ensure_ascii=False, default=_json_serializer))
        await self.client.expire(key, ttl or SESSION_CACHE_TTL)
