import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Any
from pydantic import BaseModel

# Custom log levels
ES_LOG = 15
AGENT_LOG = 16

logging.addLevelName(ES_LOG, "ESLOG")
logging.addLevelName(AGENT_LOG, "AGENTLOG")

class LoggerExtraData(BaseModel):
    logType: str
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
        self._log(ES_LOG, msg.model_dump_json(), args, **kwargs)

def agentlog(self: logging.Logger, msg: LoggerExtraData, *args: Any, **kwargs: Any) -> None:    
    if self.isEnabledFor(AGENT_LOG):
        kwargs.setdefault("stacklevel", 2)  # report caller of eslog()
        self._log(AGENT_LOG, msg.model_dump_json(), args, **kwargs)

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

    # ES_LOG(15) 레벨의 로그를 기록할 수 있도록 logger 레벨을 설정한다.
    # (기본 root 레벨이 INFO(20)이면 ES_LOG가 필터링되므로 별도 설정 필요)
    if logger.level == logging.NOTSET or logger.level > ES_LOG:
        logger.setLevel(ES_LOG)

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