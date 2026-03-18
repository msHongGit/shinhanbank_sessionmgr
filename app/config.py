"""Session Manager - Configuration Settings."""

import ast
import logging
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

# On-Prem Sentinel용 설정 (선택적)
_raw_sentinel_nodes = os.getenv("REDIS_SENTINEL_NODES", "")
if _raw_sentinel_nodes:
    try:
        # 예: REDIS_SENTINEL_NODES=[["172.23.254.140",5001],["172.23.254.140",5002]]
        REDIS_SENTINEL_NODES: list[tuple[str, int]] = [
            (str(host), int(port)) for host, port in ast.literal_eval(_raw_sentinel_nodes)
        ]
    except (ValueError, SyntaxError, TypeError) as e:
        logging.warning("REDIS_SENTINEL_NODES 파싱 실패 — Sentinel 비활성화: value=%r, reason=%s", _raw_sentinel_nodes, e)
        REDIS_SENTINEL_NODES = []
else:
    REDIS_SENTINEL_NODES = []

REDIS_SENTINEL_MASTER_NAME: str | None = os.getenv("REDIS_SENTINEL_MASTER_NAME")
REDIS_USERNAME: str | None = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD")
REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

# === TTL Settings ===
# 기본 TTL은 300초(5분)로 설정하며, 환경변수로 오버라이드 가능
SESSION_CACHE_TTL: int = int(os.getenv("SESSION_CACHE_TTL", "300"))

# === Session ID Prefix ===
GLOBAL_SESSION_PREFIX: str = os.getenv("GLOBAL_SESSION_PREFIX", "gsess")

# === JWT Configuration ===
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ACCESS_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_SECONDS", "300"))  # 5분 = 300초
JWT_REFRESH_TOKEN_EXPIRE_SECONDS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_SECONDS", "330"))  # 5분 30초

# === ES Log Configuration (optional) ===
# ES_LOG_PATH는 ES 전용 로그(eslog_*.log)를 남길 디렉터리 경로입니다.
# logger_config.setup_es_logger() 에서 직접 환경변수를 읽어 사용하지만,
# 설정을 한 곳에서 확인할 수 있도록 여기에서도 상수로 노출합니다.
ES_LOG_PATH: str = os.getenv("ES_LOG_PATH", "eslogs")

# === MinIO Configuration ===
MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "")
MINIO_ACCESS_KEY: str | None = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY: str | None = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "shinhanobj")

# === Batch Profile Decryption ===
# 암호화 키는 IniSafe Paccel(app.utils.inisafe.IniSafePaccel)에서 조회합니다.
# ENCRYPTION_KEY 환경변수는 더 이상 사용하지 않습니다.

# === Log Encryption ===
# LOG_ENCRYPT_ENABLED=true  → payload 암호화 (운영)
# LOG_ENCRYPT_ENABLED=false → 평문 로그 (개발/디버그)
LOG_ENCRYPT_ENABLED: bool = os.getenv("LOG_ENCRYPT_ENABLED", "false").lower() == "true"
# LOG_ENCRYPTION_SECRET, LOG_ENCRYPTION_SALT, HSM_*, INISAFE_ENABLED 등 구 환경변수는 제거됨
# 암호화는 모두 app.utils.inisafe.IniSafePaccel 단일 출처로 통일되었습니다.
