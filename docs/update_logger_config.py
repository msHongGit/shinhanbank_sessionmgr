import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Any
from pydantic import BaseModel
import json
import copy
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Custom log levels
ES_LOG = 15
AGENT_LOG = 16

logging.addLevelName(ES_LOG, "ESLOG")
logging.addLevelName(AGENT_LOG, "AGENTLOG")

# Encryption key for payload encryption (should be loaded from env in production)
_ENCRYPTION_KEY = None

ENCRPPT_EXCEPTIONS = [
    "globId",
    "resultCode",
    "requestId",
    "trxCd",
    "agent",
    "session_id",
    "turn_id",
]

def _get_encryption_key() -> bytes:
    """Get or generate encryption key for payload encryption."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        # In production, load from environment variable or secure key management
        secret = os.getenv("LOG_ENCRYPTION_SECRET", "default-log-encryption-secret-key-change-in-production")
        salt = os.getenv("LOG_ENCRYPTION_SALT", "default-log-encryption-salt").encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        _ENCRYPTION_KEY = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return _ENCRYPTION_KEY

def encrypt_payload(payload: Any) -> Any:
    """
    Encrypt each property in the payload object.
    
    Args:
        payload: The payload object to encrypt (can be dict, list, Pydantic model, or any object)
        
    Returns:
        Payload with each property encrypted individually
    """
    try:
        fernet = Fernet(_get_encryption_key())
        
        def encrypt_value(value: Any) -> str | None:
            if value is None:
                return value
            
            """Encrypt a single value and return as base64 string."""
            value_json = json.dumps(value, ensure_ascii=False, default=str)

            if value_json is None:
                return None
            
            encrypted = fernet.encrypt(value_json.encode('utf-8'))
            return encrypted.decode('ascii')
        
        def to_dict(obj: Any) -> Any:
            """Convert object to dict representation."""
            if isinstance(obj, dict):
                return obj
            elif isinstance(obj, list):
                return obj
            elif isinstance(obj, BaseModel):
                return obj.model_dump()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return obj
        
        def encrypt_recursive(data: Any, depth: int = 0, max_depth: int = 20) -> Any:
            """Recursively encrypt each property/item."""
            if depth > max_depth:
                return "[MAX_DEPTH_EXCEEDED]"
            
            # Convert object to dict first
            data = to_dict(data)
            
            if isinstance(data, dict):
                # Encrypt each value in the dictionary, except whitelisted keys
                return {key: value if key in ENCRPPT_EXCEPTIONS else encrypt_recursive(value) for key, value in data.items()}
            elif isinstance(data, list):
                # Encrypt each item in the list
                return [encrypt_recursive(item) for item in data]
            else:
                # Encrypt primitive values
                return encrypt_value(data)
        
        return encrypt_recursive(payload)
    except ValueError as e:
        return f"[ENCRYPTION_ERROR: ValueError - {str(e)}]"
    except TypeError as e:
        return f"[ENCRYPTION_ERROR: TypeError - {str(e)}]"
    except InvalidToken as e:
        return f"[ENCRYPTION_ERROR: InvalidToken - {str(e)}]"
    except Exception as e:
        return f"[ENCRYPTION_ERROR: {str(e)}]"

class LoggerExtraData(BaseModel):
    """Structured logging extra fields for context propagation."""
    logType: str = "-"
    custNo: str = "-"
    sessionId: str = "-"
    turnId: str = "-"
    agentId: str = "-"
    transactionId: str = "-"
    payload: object

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for use in logger.extra parameter."""
        return self.model_dump()

def eslog(self: logging.Logger, msg: LoggerExtraData, *args: Any, **kwargs: Any) -> None:
    if self.isEnabledFor(ES_LOG):
        kwargs.setdefault("stacklevel", 2)  # report caller of eslog()
        # encrypt all properties in msg.payload
        msg_copy = copy.deepcopy(msg)
        msg_copy.payload = encrypt_payload(msg_copy.payload)
        self._log(ES_LOG, msg_copy.model_dump_json(), args, **kwargs)

def agentlog(self: logging.Logger, msg: LoggerExtraData, *args: Any, **kwargs: Any) -> None:    
    if self.isEnabledFor(AGENT_LOG):
        kwargs.setdefault("stacklevel", 2)  # report caller of agentlog()
        # encrypt all properties in msg.payload
        msg_copy = copy.deepcopy(msg)
        msg_copy.payload = encrypt_payload(msg_copy.payload)
        self._log(AGENT_LOG, msg_copy.model_dump_json(), args, **kwargs)

logging.Logger.eslog = eslog  # type: ignore[attr-defined]
logging.Logger.agentlog = agentlog  # type: ignore[attr-defined]

class OnlyESLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == ES_LOG or record.levelno == AGENT_LOG


class ExcludeESLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno != ES_LOG and record.lineno != AGENT_LOG


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
    # Note: setLevel and propagate are handled by loging_config.py setup_logging()
    # to ensure proper logger hierarchy for child loggers using __name__

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d %(funcName)s() - %(message)s"
    )

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