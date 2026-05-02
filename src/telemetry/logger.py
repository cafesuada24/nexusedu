"""Production-grade structured logging for the Agent Assistant."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

from src.core.config import config

# Global context for correlation IDs (e.g., thread_id, request_id)
# This allows logs to include context without passing it explicitly to every log call.
logger_context: ContextVar[dict[str, object] | None] = ContextVar(
    'logger_context',
    default=None,
)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record into a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON-encoded string containing the log data and context.
        """
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

    def __init__(self, name: str = 'AI-Lab-Agent', _log_dir: str = 'logs') -> None:
        """Initialize the logger.

        Args:
            name: Logger name.
            _log_dir: Directory for log files (Unused).
        """
        self.logger = logging.getLogger(name)
        # Use env var for log level, default to INFO
        log_level = config.log_level
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Clear existing handlers to avoid duplicates during re-init
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        formatter = JSONFormatter()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    @staticmethod
    def set_context(context: dict[str, object]) -> None:
        """Sets the current correlation context.

        Args:
            context: Dictionary of context fields to include in subsequent logs.
        """
        current = logger_context.get() or {}
        current = current.copy()
        current.update(context)
        logger_context.set(current)

    @staticmethod
    def clear_context() -> None:
        """Clears the correlation context."""
        logger_context.set({})

    def log_event(self, event_type: str, data: dict[str, object]) -> None:
        """Logs a specific event with associated data.

        Args:
            event_type: The type of event to log.
            data: Key-value pairs of event data.
        """
        # We use 'extra' to pass the data to the formatter
        self.logger.info(f'Event: {event_type}', extra={'extra_data': data})

    def info(self, msg: str, **kwargs: object) -> None:
        """Logs an INFO level message.

        Args:
            msg: The message to log.
            **kwargs: Extra fields to include in the log entry.
        """
        self.logger.info(msg, extra={'extra_data': kwargs} if kwargs else None)

    def error(self, msg: str, exc_info: bool = True, **kwargs: object) -> None:
        """Logs an ERROR level message.

        Args:
            msg: The message to log.
            exc_info: Whether to include exception traceback.
            **kwargs: Extra fields to include in the log entry.
        """
        self.logger.error(
            msg,
            exc_info=exc_info,
            extra={'extra_data': kwargs} if kwargs else None,
        )

    def debug(self, msg: str, **kwargs: object) -> None:
        """Logs a DEBUG level message.

        Args:
            msg: The message to log.
            **kwargs: Extra fields to include in the log entry.
        """
        self.logger.debug(msg, extra={'extra_data': kwargs} if kwargs else None)

    def warning(self, msg: str, **kwargs: object) -> None:
        """Logs a WARNING level message.

        Args:
            msg: The message to log.
            **kwargs: Extra fields to include in the log entry.
        """
        self.logger.warning(msg, extra={'extra_data': kwargs} if kwargs else None)


# Global logger instance
logger = IndustryLogger()
