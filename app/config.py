"""Session Manager - Configuration Settings (v3.0)."""

import os
import re
from pathlib import Path

# === .env 파일 로드 (로컬 개발용) ===


def load_env_file():
    """Load .env file for local development with variable expansion."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # ${VAR} 형식의 변수 치환
                    def replace_var(match):
                        var_name = match.group(1)
                        return os.environ.get(var_name, match.group(0))

                    value = re.sub(r"\$\{([^}]+)\}", replace_var, value)
                    os.environ.setdefault(key, value)


load_env_file()

# === Application Settings ===
APP_ENV: str = os.getenv("APP_ENV", "dev")
DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# === CORS ===
ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# === Redis Configuration ===
#
# 기본값은 Azure Redis 인스턴스를 가리키며,
# 환경별(예: 온프렘)로는 반드시 REDIS_URL 환경 변수로 오버라이드해서 사용합니다.
#
# 예) Azure Redis (비밀번호는 시크릿에서 REDIS_PASSWORD 로 주입)
#   export REDIS_URL="rediss://default:${REDIS_PASSWORD}@redis-shinhan-sol-test.koreacentral.redis.azure.net:10000/0"
#
# 예) 온프렘 Redis (요청하신 온프렘 환경 정보 기준)
#   export REDIS_URL="redis://redis-stack.sas-portal-dev:6379/0"

REDIS_URL: str = os.getenv(
    "REDIS_URL", "rediss://default:40eMR6v24M6rghbwNjZeAZJxZIABPERQHAzCaFCHkJY=@redis-shinhan-sol-test.koreacentral.redis.azure.net:10000/0"
)
REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))

# === TTL Settings ===
# 기본 TTL은 600초(5분)로 설정하며, 환경변수로 오버라이드 가능
SESSION_CACHE_TTL: int = int(os.getenv("SESSION_CACHE_TTL", "600"))
SESSION_MAP_TTL: int = int(os.getenv("SESSION_MAP_TTL", "600"))

# === PostgreSQL (향후 사용) ===
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/session_manager",
)
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

# === Session ID Prefix ===
GLOBAL_SESSION_PREFIX: str = os.getenv("GLOBAL_SESSION_PREFIX", "gsess")
LOCAL_SESSION_PREFIX: str = os.getenv("LOCAL_SESSION_PREFIX", "lsess")
CONVERSATION_ID_PREFIX: str = os.getenv("CONVERSATION_ID_PREFIX", "conv")
CONTEXT_ID_PREFIX: str = os.getenv("CONTEXT_ID_PREFIX", "ctx")

# === API Keys (호출자별) ===
AGW_API_KEY: str = os.getenv("AGW_API_KEY", "agw-api-key")
MA_API_KEY: str = os.getenv("MA_API_KEY", "ma-api-key")
PORTAL_API_KEY: str = os.getenv("PORTAL_API_KEY", "portal-api-key")
VDB_API_KEY: str = os.getenv("VDB_API_KEY", "vdb-api-key")
CLIENT_API_KEY: str = os.getenv("CLIENT_API_KEY", "client-api-key")
EXTERNAL_API_KEY: str = os.getenv("EXTERNAL_API_KEY", "external-api-key")  # Sprint 3

# === Auth (Sprint 2: 기본 비활성화, 운영에서만 활성화 권장) ===
ENABLE_API_KEY_AUTH: bool = os.getenv("ENABLE_API_KEY_AUTH", "false").lower() == "true"
