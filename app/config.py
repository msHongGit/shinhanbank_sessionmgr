"""Session Manager - Configuration Settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

CONFIG_ENV_PATH = Path(__file__).with_suffix(".env")
if CONFIG_ENV_PATH.exists():
    load_dotenv(dotenv_path=CONFIG_ENV_PATH, override=False)

# === Application Settings ===
APP_ENV: str = os.getenv("APP_ENV", "dev")
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# === CORS ===
ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# === Redis Configuration ===

REDIS_URL: str | None = os.getenv("REDIS_URL")
REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))

# Redis Mock 모드 플래그 (테스트/스모크용)
# - true 이면 Redis 대신 In-Memory MockRepository를 사용한다.
USE_MOCK_REDIS: bool = os.getenv("USE_MOCK_REDIS", "false").lower() == "true"

# === TTL Settings ===
# 기본 TTL은 600초(5분)로 설정하며, 환경변수로 오버라이드 가능
SESSION_CACHE_TTL: int = int(os.getenv("SESSION_CACHE_TTL", "600"))
SESSION_MAP_TTL: int = int(os.getenv("SESSION_MAP_TTL", "600"))

# === PostgreSQL (향후 사용) ===
# 현재 Sprint 3에서는 사용하지 않으며, 향후 RDB 연동 시 활용 예정이다.
DATABASE_URL: str | None = os.getenv("DATABASE_URL")
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

# === Session ID Prefix ===
GLOBAL_SESSION_PREFIX: str = os.getenv("GLOBAL_SESSION_PREFIX", "gsess")
LOCAL_SESSION_PREFIX: str = os.getenv("LOCAL_SESSION_PREFIX", "lsess")
CONVERSATION_ID_PREFIX: str = os.getenv("CONVERSATION_ID_PREFIX", "conv")
CONTEXT_ID_PREFIX: str = os.getenv("CONTEXT_ID_PREFIX", "ctx")

# === API Keys (호출자별) ===
AGW_API_KEY: str = os.getenv("AGW_API_KEY", "")
MA_API_KEY: str = os.getenv("MA_API_KEY", "")
PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "")
VDB_API_KEY: str = os.getenv("VDB_API_KEY", "")
CLIENT_API_KEY: str = os.getenv("CLIENT_API_KEY", "")
EXTERNAL_API_KEY: str = os.getenv("EXTERNAL_API_KEY", "")  # Sprint 3

# === Auth (Sprint 2: 기본 비활성화, 운영에서만 활성화 권장) ===
ENABLE_API_KEY_AUTH: bool = os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true"
