"""
Session Manager - Configuration Settings (v3.0)
"""

from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App
    APP_ENV: str = "dev"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Redis (Azure Redis Cache - 환경변수 필수)
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 10

    # TTL Settings
    SESSION_CACHE_TTL: int = 3600  # 1 hour - Global Session
    LOCAL_SESSION_TTL: int = 1800  # 30 min - Local Session
    SESSION_MAP_TTL: int = 3600  # 1 hour - Global↔Local 매핑

    # PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/session_manager"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Session ID Prefix
    GLOBAL_SESSION_PREFIX: str = "gsess"
    LOCAL_SESSION_PREFIX: str = "lsess"
    CONVERSATION_ID_PREFIX: str = "conv"
    CONTEXT_ID_PREFIX: str = "ctx"

    # API Keys (호출자별)
    AGW_API_KEY: str = "agw-api-key"
    MA_API_KEY: str = "ma-api-key"
    PORTAL_API_KEY: str = "portal-api-key"
    VDB_API_KEY: str = "vdb-api-key"

    # Auth (Sprint 2: 기본 비활성화, 운영에서만 활성화 권장)
    ENABLE_API_KEY_AUTH: bool = False

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
