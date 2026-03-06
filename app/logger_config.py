import base64
import copy
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel
from pydantic_core import PydanticSerializationError

from app.config import (
    HSM_ENABLED,
    HSM_KEY_LABEL,
    HSM_LIB_PATH,
    HSM_PIN,
    HSM_TOKEN_LABEL,
    LOG_ENCRYPT_ENABLED,
    LOG_ENCRYPTION_SALT,
    LOG_ENCRYPTION_SECRET,
)

# Custom log levels
ES_LOG = 15
AGENT_LOG = 16

logging.addLevelName(ES_LOG, "ESLOG")
logging.addLevelName(AGENT_LOG, "AGENTLOG")

# 암호화 제외 컬럼명 목록
# 이 리스트에 키 이름을 추가하면 해당 필드 값은 암호화되지 않습니다.
ENCRYPT_EXCEPTIONS: list[str] = [
    "globId",
    "resultCode",
    "requestId",
    "trxCd",
    "agent",
    "session_id",
    "turn_id",
]

_ENCRYPTION_KEY: bytes | None = None


def _get_key_from_hsm() -> bytes:
    """HSM 에서 AES 키를 가져와 Fernet 호환 base64url 키로 반환합니다.

    고객사 SDK 교체 시 이 함수 내부만 수정하세요.
    방식 1) PKCS#11 표준 (python-pkcs11)  ← 현재 기본
    방식 2) 고객사 자체 SDK          ← 하단 주석 해제
    """
    if not HSM_LIB_PATH:
        raise RuntimeError("HSM_LIB_PATH is not set")
    if not HSM_PIN:
        raise RuntimeError("HSM_PIN is not set")
    if not HSM_KEY_LABEL:
        raise RuntimeError("HSM_KEY_LABEL is not set")

    # ── 방식 1: PKCS#11 표준 ──────────────────────────────────
    try:
        import pkcs11  # type: ignore[import]  # uv add python-pkcs11
        from pkcs11 import KeyType, ObjectClass  # type: ignore[import]

        lib = pkcs11.lib(HSM_LIB_PATH)
        token = lib.get_token(token_label=HSM_TOKEN_LABEL or "default")
        with token.open(user_pin=HSM_PIN) as session:
            key = session.get_key(
                object_class=ObjectClass.SECRET_KEY,
                key_type=KeyType.AES,
                label=HSM_KEY_LABEL,
            )
            raw_key: bytes = key[pkcs11.Attribute.VALUE]
            return base64.urlsafe_b64encode(raw_key[:32])
    except ImportError as exc:
        raise RuntimeError("python-pkcs11 없음: uv add python-pkcs11") from exc
    except Exception as exc:
        raise RuntimeError(f"[HSM] 키 조회 실패: {exc}") from exc

    # ── 방식 2: 고객사 자체 SDK (주석 해제 후 사용) ────────────────
    # from shinhan_crypto_sdk import CryptoClient
    # client = CryptoClient(
    #     endpoint=os.getenv("CRYPTO_SDK_URL"),
    #     api_key=os.getenv("CRYPTO_SDK_API_KEY"),
    # )
    # raw_key: bytes = client.get_key(label=HSM_KEY_LABEL)
    # return base64.urlsafe_b64encode(raw_key[:32])


def _get_encryption_key() -> bytes:
    """
    암호화 키를 반환합니다. (싱글턴)

    HSM_ENABLED=true  → _get_key_from_hsm() 호출
    HSM_ENABLED=false → LOG_ENCRYPTION_SECRET 기반 PBKDF2 키 생성
    """
    global _ENCRYPTION_KEY  # noqa: PLW0603
    if _ENCRYPTION_KEY is None:
        if HSM_ENABLED:
            _ENCRYPTION_KEY = _get_key_from_hsm()
        else:
            if not LOG_ENCRYPTION_SECRET:
                raise RuntimeError("LOG_ENCRYPTION_SECRET is not set")
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=LOG_ENCRYPTION_SALT.encode(),
                iterations=100_000,
            )
            _ENCRYPTION_KEY = base64.urlsafe_b64encode(kdf.derive(LOG_ENCRYPTION_SECRET.encode()))
    return _ENCRYPTION_KEY


def encrypt_payload(payload: Any) -> Any:
    """payload 내 각 속성을 개별 암호화합니다.

    ENCRYPT_EXCEPTIONS 에 등록된 키는 암호화에서 제외됩니다.

    Args:
        payload: 암호화할 payload (dict, list, BaseModel, 기타 객체)

    Returns:
        각 속성이 개별 암호화된 payload
    """
    try:
        fernet = Fernet(_get_encryption_key())

        def encrypt_value(value: Any) -> str | None:
            """단일 값을 암호화하여 ASCII 문자열로 반환합니다."""
            if value is None:
                return value
            value_json = json.dumps(value, ensure_ascii=False, default=str)
            encrypted = fernet.encrypt(value_json.encode("utf-8"))
            return encrypted.decode("ascii")

        def to_dict(obj: Any) -> Any:
            """객체를 dict/list 표현으로 변환합니다."""
            if isinstance(obj, dict):
                return obj
            elif isinstance(obj, list):
                return obj
            elif isinstance(obj, BaseModel):
                return obj.model_dump()
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                return obj

        def encrypt_recursive(data: Any, depth: int = 0, max_depth: int = 20) -> Any:
            """각 속성/항목을 재귀적으로 암호화합니다."""
            if depth > max_depth:
                return "[MAX_DEPTH_EXCEEDED]"

            data = to_dict(data)

            if isinstance(data, dict):
                return {
                    key: (
                        value  # ENCRYPT_EXCEPTIONS 키는 암호화 제외
                        if key in ENCRYPT_EXCEPTIONS
                        else encrypt_recursive(value, depth + 1, max_depth)
                    )
                    for key, value in data.items()
                }
            elif isinstance(data, list):
                return [encrypt_recursive(item, depth + 1, max_depth) for item in data]
            else:
                return encrypt_value(data)

        return encrypt_recursive(payload)

    except ValueError as e:
        return f"[ENCRYPTION_ERROR: ValueError - {e}]"
    except TypeError as e:
        return f"[ENCRYPTION_ERROR: TypeError - {e}]"
    except InvalidToken as e:
        return f"[ENCRYPTION_ERROR: InvalidToken - {e}]"
    except Exception as e:  # noqa: BLE001
        return f"[ENCRYPTION_ERROR: {e}]"


class LoggerExtraData(BaseModel):
    logType: str  # noqa: N815
    custNo: str = "-"  # noqa: N815
    sessionId: str = "-"  # noqa: N815
    turnId: str = "-"  # noqa: N815
    agentId: str = "-"  # noqa: N815
    transactionId: str = "-"  # noqa: N815
    payload: object

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for use in logger.extra parameter."""
        return self.model_dump()
def eslog(self: logging.Logger, msg: LoggerExtraData, *args: Any, **kwargs: Any) -> None:
    """ES 로그 헬퍼 (직렬화 에러 디버그용)."""
    if not self.isEnabledFor(ES_LOG):
        return

    try:
        msg_copy = copy.deepcopy(msg)
        if LOG_ENCRYPT_ENABLED:
            msg_copy.payload = encrypt_payload(msg_copy.payload)
        kwargs.setdefault("stacklevel", 2)  # report caller of eslog()
        self._log(ES_LOG, msg_copy.model_dump_json(), args, **kwargs)
    except PydanticSerializationError as exc:  # pragma: no cover - 디버그용 경로
        print("=== ESLOG SERIALIZATION ERROR ===")
        print("type(msg):", type(msg))
        print("msg.__dict__:", msg.__dict__)
        raise exc


def agentlog(self: logging.Logger, msg: LoggerExtraData, *args: Any, **kwargs: Any) -> None:
    if self.isEnabledFor(AGENT_LOG):
        msg_copy = copy.deepcopy(msg)
        if LOG_ENCRYPT_ENABLED:
            msg_copy.payload = encrypt_payload(msg_copy.payload)
        kwargs.setdefault("stacklevel", 2)  # report caller of agentlog()
        self._log(AGENT_LOG, msg_copy.model_dump_json(), args, **kwargs)


logging.Logger.eslog = eslog  # type: ignore[attr-defined]
logging.Logger.agentlog = agentlog  # type: ignore[attr-defined]


class OnlyESLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == ES_LOG or record.levelno == AGENT_LOG


class ExcludeESLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno not in (ES_LOG, AGENT_LOG)


def _ensure_handler_once(logger: logging.Logger, handler: logging.Handler) -> None:
    # 같은 타입+같은 파일이면 중복 추가 방지
    target = getattr(handler, "baseFilename", None)
    for h in logger.handlers:
        if type(h) is type(handler) and getattr(h, "baseFilename", None) == target:
            return
    logger.addHandler(handler)


def setup_es_logger(log_dir: str | None = None, pod_uid: str | None = None) -> logging.Logger:
    if log_dir is None:
        log_dir = os.getenv("ES_LOG_PATH", "/eslog")

    os.makedirs(log_dir, exist_ok=True)

    # Get pod_uid from parameter or environment variable (set via Kubernetes downward API)
    if pod_uid is None:
        pod_uid = os.getenv("POD_UID") or os.getenv("POD_NAME") or os.getenv("HOSTNAME") or "default"

    logger = logging.getLogger("app")

    # ES_LOG(15) 레벨의 로그를 기록할 수 있도록 logger 레벨을 설정한다.
    # (기본 root 레벨이 INFO(20)이면 ES_LOG가 필터링되므로 별도 설정 필요)
    if logger.level == logging.NOTSET or logger.level > ES_LOG:
        logger.setLevel(ES_LOG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(funcName)s() - %(message)s")

    # eslog.log: ES_LOG only - use pod_uid in filename
    log_filename = f"eslog_{pod_uid}.log"
    eslog_h = TimedRotatingFileHandler(
        os.path.join(log_dir, log_filename),
        when="midnight",
        interval=1,
        backupCount=int(os.getenv("ES_LOG_BACKUP_COUNT", 7)),
        encoding="utf-8",
        utc=False,
    )
    eslog_h.setFormatter(fmt)
    eslog_h.addFilter(OnlyESLogFilter())
    _ensure_handler_once(logger, eslog_h)

    return logger
