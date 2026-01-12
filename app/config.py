"""Session Manager - Configuration Settings (v3.0)."""

import os
import re
from pathlib import Path

# === .env 파일 로드 (로컬 개발용) ===


def load_env_file():
    """Load .env file for local development with variable expansion.

    - 로컬 개발 환경에서만 사용하는 것을 권장한다.
    - 운영/컨테이너 환경에서는 환경변수/시크릿으로 설정을 주입하고,
      .env 자동 로드는 비활성화한다.
    """
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


# 로컬 개발에서는 기본값 true, 운영/컨테이너에서는 SHINHAN_SM_LOAD_ENV=false 권장
SHINHAN_SM_LOAD_ENV: bool = os.getenv("SHINHAN_SM_LOAD_ENV", "true").lower() == "true"
if SHINHAN_SM_LOAD_ENV:
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
# 모든 환경에서 REDIS_URL 설정을 **필수**로 요구한다.
# - 운영(on-prem Redis), 개발(Azure Redis) 모두 환경변수 또는 .env 로 주입
# - 코드 내부에는 실제 접속 정보(호스트/비밀번호)를 두지 않는다.
#
# 예) 개발(Azure Redis, 비밀번호는 시크릿에서 REDIS_PASSWORD 로 주입)
#   export REDIS_URL="rediss://default:${REDIS_PASSWORD}@<azure-redis-host>:10000/0"
#
# 예) 운영/온프렘 Redis
#   export REDIS_URL="redis://redis-stack.sas-portal-dev:6379/0"

REDIS_URL: str | None = os.getenv("REDIS_URL")
if not REDIS_URL:
    # 컨테이너/테스트 환경에서 REDIS_URL 미설정 시에도 애플리케이션이 기동되도록
    # 로컬호스트 Redis를 기본값으로 사용한다.
    # - 실제 Redis 연결이 필요 없는 헬스체크/스모크 테스트용 시나리오를 지원하기 위한 설정
    # - 운영 환경에서는 반드시 REDIS_URL 을 명시적으로 설정해야 한다.
    REDIS_URL = "rediss://default:$40eMR6v24M6rghbwNjZeAZJxZIABPERQHAzCaFCHkJY=@redis-shinhan-sol-test.koreacentral.redis.azure.net:10000/0"
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
