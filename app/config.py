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

# === MariaDB Configuration ===
MARIADB_HOST: str = os.getenv("MARIADB_HOST", "localhost")
MARIADB_PORT: int = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER: str = os.getenv("MARIADB_USER", "test_user")
MARIADB_PASSWORD: str = os.getenv("MARIADB_PASSWORD", "test_password")
MARIADB_DATABASE: str = os.getenv("MARIADB_DATABASE", "session_manager")
MARIADB_POOL_SIZE: int = int(os.getenv("MARIADB_POOL_SIZE", "10"))
MARIADB_MAX_OVERFLOW: int = int(os.getenv("MARIADB_MAX_OVERFLOW", "20"))
MARIADB_POOL_RECYCLE: int = int(os.getenv("MARIADB_POOL_RECYCLE", "3600"))
MARIADB_ECHO: bool = os.getenv("MARIADB_ECHO", "false").lower() == "true"

# MariaDB 연결 활성화 여부 (test_user/test_password가 아니면 활성화)
USE_MARIADB: bool = not (MARIADB_USER == "test_user" and MARIADB_PASSWORD == "test_password")

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
