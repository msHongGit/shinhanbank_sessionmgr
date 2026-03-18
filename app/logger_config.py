import base64
import copy
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import BaseModel
from pydantic_core import PydanticSerializationError

from app.config import (
    LOG_ENCRYPT_ENABLED,
)
from app.utils.inisafe import IniSafePaccel, ISPSymmKey

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

_INISAFE_KEY: ISPSymmKey | None = None


def _get_encryption_key() -> ISPSymmKey:
    """IniSafe Paccel 에서 대칭키(ISPSymmKey)를 조회합니다. (싱글턴)

    Returns:
        ISPSymmKey: .symmKey (hex AES 키) + .symmIV (hex IV)
    """
    global _INISAFE_KEY  # noqa: PLW0603
    if _INISAFE_KEY is None:
        inisafe = IniSafePaccel()
        _INISAFE_KEY = inisafe.get_symm_key()
    return _INISAFE_KEY


def encrypt_payload(payload: Any) -> Any:
    """payload 내 각 속성을 IniSafe AES/GCM 으로 개별 암호화합니다.

    ENCRYPT_EXCEPTIONS 에 등록된 키는 암호화에서 제외됩니다.

    Args:
        payload: 암호화할 payload (dict, list, BaseModel, 기타 객체)

    Returns:
        각 속성이 개별 암호화된 payload
    """
    try:
        symm_key: ISPSymmKey = _get_encryption_key()
        aes_key = bytes.fromhex(symm_key.symmKey)
        iv = bytes.fromhex(symm_key.symmIV)

        def encrypt_value(value: Any) -> str | None:
            """AES/GCM + PKCS7 패딩으로 단일 값을 암호화하여 base64url 문자열로 반환."""
            if value is None:
                return value
            value_json = json.dumps(value, ensure_ascii=False, default=str)
            cipher = Cipher(algorithms.AES(aes_key), modes.GCM(iv)).encryptor()
            padder = padding.PKCS7(128).padder()
            padded = padder.update(value_json.encode("utf-8")) + padder.finalize()
            encrypted = cipher.update(padded) + cipher.finalize()
            encrypted_with_iv = iv + encrypted
            return base64.urlsafe_b64encode(encrypted_with_iv).decode("ascii")

        def to_dict(obj: Any) -> Any:
            """obj를 dict/list 표현으로 변환."""
            if isinstance(obj, (dict, list)):
                return obj
            elif isinstance(obj, BaseModel):
                return obj.model_dump()
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            return obj

        def encrypt_recursive(data: Any, depth: int = 0, max_depth: int = 20) -> Any:
            """dict/list 재귀 암호화."""
            if depth > max_depth:
                return "[MAX_DEPTH_EXCEEDED]"
            data = to_dict(data)
            if isinstance(data, dict):
                return {
                    key: (
                        value
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
