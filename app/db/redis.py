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

    # ============ JTI Mapping ============

    def set_jti_mapping(self, jti: str, global_session_key: str, ttl: int = 300) -> None:
        """jti -> global_session_key 매핑 저장
        
        Args:
            jti: JWT ID (UUID)
            global_session_key: Global 세션 키
            ttl: TTL (초 단위, 기본값 300초)
        """
        self.client.setex(f"jti:{jti}", ttl, global_session_key)

    def get_global_session_key_by_jti(self, jti: str) -> str | None:
        """jti로 global_session_key 조회
        
        Args:
            jti: JWT ID (UUID)
            
        Returns:
            global_session_key 또는 None
        """
        result = self.client.get(f"jti:{jti}")
        if result:
            return result if isinstance(result, str) else result.decode()
        return None

    # ============ 실시간 프로파일 ============

    def get_realtime_profile(self, user_id: str) -> dict[str, Any] | None:
        """실시간 프로파일 조회
        
        Args:
            user_id: 사용자 ID (10자리 숫자, 예: "0616001905")
            
        Returns:
            실시간 프로파일 데이터 (dict) 또는 None
        """
        data = self.client.get(f"profile:realtime:{user_id}")
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_realtime_profile(self, user_id: str, profile_data: dict[str, Any]) -> None:
        """실시간 프로파일 저장 (TTL 없음, 영구 저장)
        
        Args:
            user_id: 사용자 ID (10자리 숫자, 예: "0616001905")
            profile_data: 실시간 프로파일 데이터 (dict, redis_data.md 구조 그대로 저장)
        """
        key = f"profile:realtime:{user_id}"
        self.client.set(key, json.dumps(profile_data, ensure_ascii=False))

    # ============ 배치 프로파일 ============

    def get_batch_profile(self, user_id: str) -> dict[str, Any] | None:
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
        data = self.client.get(f"profile:batch:{user_id}")
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_batch_profile(self, user_id: str, profile_data: dict[str, Any]) -> None:
        """배치 프로파일 저장 (TTL 없음, 영구 저장)
        
        Args:
            user_id: 사용자 ID (10자리 숫자, 예: "0616001905")
            profile_data: 배치 프로파일 데이터 (dict)
            {
                "daily": {...},    # IFC_CUS_DD_SMRY_TOT 테이블 데이터
                "monthly": {...}   # IFC_CUS_MMBY_SMRY_TOT 테이블 데이터
            }
        """
        key = f"profile:batch:{user_id}"
        self.client.set(key, json.dumps(profile_data, ensure_ascii=False))
