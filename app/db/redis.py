"""
Session Manager - Redis Connection
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings

_redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global _redis_client
    _redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
    )
    # Test connection
    await _redis_client.ping()
    print("✅ Redis connected")


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        print("❌ Redis disconnected")


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance"""
    if not _redis_client:
        await init_redis()
    return _redis_client
