import logging


class OneLineErrorFormatter(logging.Formatter):
    """ERROR 로그를 한 줄로 포맷팅한다."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        message_body = record.message
        trace_id = getattr(record, "otelTraceID", "-")
        span_id = getattr(record, "otelSpanID", "-")
        otel_prefix = f"[trace={trace_id} span={span_id}]"

        if record.levelno >= logging.ERROR:
            message_body = f"errmsg: {message_body}"

        record.message = f"{otel_prefix} {message_body}".strip()

        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        formatted = self.formatMessage(record)

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if record.levelno >= logging.ERROR:
                formatted = f"{formatted} stack_trace: {exc_text.replace(chr(10), r'\\n')}"
            else:
                formatted = f"{formatted}\n{exc_text}"

        if record.stack_info:
            stack_text = self.formatStack(record.stack_info)
            if record.levelno >= logging.ERROR:
                formatted = f"{formatted} stack_info: {stack_text.replace(chr(10), r'\\n')}"
            else:
                formatted = f"{formatted}\n{stack_text}"

        return formatted
