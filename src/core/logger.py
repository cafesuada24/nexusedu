"""Production-grade structured logging using structlog and OpenTelemetry."""

import logging
import sys
from collections.abc import Mapping, MutableMapping
from typing import TYPE_CHECKING, Any

import structlog
from opentelemetry import trace

from src.core.config import config

if TYPE_CHECKING:
    from structlog.typing import Processor


def add_opentelemetry_ids(_, __, event_dict: MutableMapping[str, Any]) -> Mapping[str, Any]:
    """Processor to add OpenTelemetry Trace and Span IDs to the log event."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.is_valid:
            # OpenTelemetry trace/span IDs are ints, format to hex strings
            event_dict['trace_id'] = format(ctx.trace_id, '032x')
            event_dict['span_id'] = format(ctx.span_id, '016x')
    return event_dict


def configure_logger() -> None:
    """Initializes structlog with a production-grade pipeline."""
    # Base logging level from config
    log_level_str = config.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Standard logging configuration for intercepting library logs (e.g., uvicorn, sqlalchemy)
    # We set it to print to stdout so it gets captured by the same pipe as structlog
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
        level=log_level,
    )

    processors: list[Processor] = [
        # Merges contextvars (bound context) into the log event
        structlog.contextvars.merge_contextvars,
        # Adds the log level (info, error, etc.)
        structlog.processors.add_log_level,
        # Formats exception info if present
        structlog.processors.format_exc_info,
        # Adds an ISO-formatted timestamp
        structlog.processors.TimeStamper(fmt='iso'),
        # Adds OpenTelemetry Trace/Span IDs for correlation
        add_opentelemetry_ids,
        # Renders the final event as a JSON string
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        # PrintLoggerFactory is fast and straightforward for containerized environments
        logger_factory=structlog.PrintLoggerFactory(),
        # Bound logger that filters based on level
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


# Initialize on import
configure_logger()

# Global logger instance for convenience
# Note: Callers can also use structlog.get_logger(__name__) for more granular control
logger = structlog.get_logger('NexusEdu')
