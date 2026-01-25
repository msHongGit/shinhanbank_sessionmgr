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

# === API Keys (호출자별) ===
AGW_API_KEY: str = os.getenv("AGW_API_KEY", "")
MA_API_KEY: str = os.getenv("MA_API_KEY", "")
PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "")
VDB_API_KEY: str = os.getenv("VDB_API_KEY", "")
CLIENT_API_KEY: str = os.getenv("CLIENT_API_KEY", "")
EXTERNAL_API_KEY: str = os.getenv("EXTERNAL_API_KEY", "")  # Sprint 3

# === Auth (Sprint 2: 기본 비활성화, 운영에서만 활성화 권장) ===
ENABLE_API_KEY_AUTH: bool = os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true"
