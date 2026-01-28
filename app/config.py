"""Session Manager - Configuration Settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

CONFIG_ENV_PATH = Path(__file__).with_suffix(".env")
if CONFIG_ENV_PATH.exists():
    load_dotenv(dotenv_path=CONFIG_ENV_PATH, override=False)

# === Application Settings ===
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")

# === CORS ===
ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# === Redis Configuration ===

REDIS_URL: str | None = os.getenv("REDIS_URL")
REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))

# === TTL Settings ===
# 기본 TTL은 300초(5분)로 설정하며, 환경변수로 오버라이드 가능
SESSION_CACHE_TTL: int = int(os.getenv("SESSION_CACHE_TTL", "300"))

# === Session ID Prefix ===
GLOBAL_SESSION_PREFIX: str = os.getenv("GLOBAL_SESSION_PREFIX", "gsess")

# === JWT Configuration ===
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_SECONDS", "300"))  # 5분 = 300초
JWT_REFRESH_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_SECONDS", "330"))  # 5분 30초

# === MariaDB Configuration ===
MARIADB_HOST: str = os.getenv("MARIADB_HOST", "")
MARIADB_PORT: int = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER: str = os.getenv("MARIADB_USER", "")
MARIADB_PASSWORD: str = os.getenv("MARIADB_PASSWORD", "")
MARIADB_DATABASE: str = os.getenv("MARIADB_DATABASE", "")
MARIADB_POOL_SIZE: int = int(os.getenv("MARIADB_POOL_SIZE", "10"))
MARIADB_MAX_OVERFLOW: int = int(os.getenv("MARIADB_MAX_OVERFLOW", "20"))
