import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Global context for correlation IDs (e.g., thread_id, request_id)
# This allows logs to include context without passing it explicitly to every log call.
logger_context: ContextVar[dict[str, object] | None] = ContextVar(
    'logger_context', default=None
)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        context = logger_context.get() or {}
        payload = {
            'timestamp': datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
            'line': record.lineno,
            **context,
        }

        # Add extra fields if they exist
        if hasattr(record, 'extra_data') and record.extra_data:
            payload['data'] = record.extra_data

        # Add exception info if it exists
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)

        return json.dumps(payload)


class IndustryLogger:
    """Production-grade structured logger.

    Supports:
    - Contextual logging (correlation IDs) via contextvars.
    - JSON formatting for both console and file.
    - Automatic log rotation (simplified).
    - Environment-based log level control.
    """

    def __init__(self, name: str = 'AI-Lab-Agent', log_dir: str = 'logs') -> None:
        self.logger = logging.getLogger(name)
        # Use env var for log level, default to INFO
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Clear existing handlers to avoid duplicates during re-init
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Skip directory creation and file handlers on read-only environments like Vercel
        # is_vercel = os.getenv("VERCEL") == "1"

        formatter = JSONFormatter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # if not is_vercel and not os.path.exists(log_dir):
        #     os.makedirs(log_dir, exist_ok=True)

            # File Handler (Optional, disabled if you want to avoid file writing entirely)
            # log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}.log')
            # file_handler = logging.FileHandler(log_file)
            # file_handler.setFormatter(formatter)
            # self.logger.addHandler(file_handler)

    @staticmethod
    def set_context(context: dict[str, object]) -> None:
        """Sets the current correlation context."""
        current = logger_context.get() or {}
        current = current.copy()
        current.update(context)
        logger_context.set(current)

    @staticmethod
    def clear_context() -> None:
        """Clears the correlation context."""
        logger_context.set({})

    def log_event(self, event_type: str, data: dict[str, object]) -> None:
        """Logs a specific event with associated data."""
        # We use 'extra' to pass the data to the formatter
        self.logger.info(f'Event: {event_type}', extra={'extra_data': data})

    def info(self, msg: str, **kwargs: object) -> None:
        self.logger.info(msg, extra={'extra_data': kwargs} if kwargs else None)

    def error(self, msg: str, exc_info: bool = True, **kwargs: object) -> None:
        self.logger.error(
            msg, exc_info=exc_info, extra={'extra_data': kwargs} if kwargs else None
        )

    def debug(self, msg: str, **kwargs: object) -> None:
        self.logger.debug(msg, extra={'extra_data': kwargs} if kwargs else None)

    def warning(self, msg: str, **kwargs: object) -> None:
        self.logger.warning(msg, extra={'extra_data': kwargs} if kwargs else None)


# Global logger instance
logger = IndustryLogger()
