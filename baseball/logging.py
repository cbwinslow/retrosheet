"""Structured logging configuration for baseball prediction warehouse.

Provides consistent, context-rich logging across the application using
structlog for JSON-structured output or console formatting.

Example:
    >>> from baseball.logging import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Starting data ingestion", source="mlb_api", season=2024)
    {"event": "Starting data ingestion", "source": "mlb_api", "season": 2024, ...}
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from baseball.core.settings import settings


def add_timestamp(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add ISO8601 timestamp to log entries."""
    import datetime

    event_dict['timestamp'] = datetime.datetime.now(
        datetime.UTC,
    ).isoformat()
    return event_dict


def add_service_info(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add service name and version to log entries."""
    event_dict['service'] = 'baseball-warehouse'
    event_dict['version'] = '0.1.0'
    return event_dict


def configure_logging(
    level: str | None = None,
    format: str | None = None,
    log_file: Path | None = None,
) -> None:
    """Configure structured logging for the application.

    Sets up both structlog for structured output and standard library
    logging for compatibility with third-party libraries.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to settings.logging.level.
        format: Output format ("json" or "console").
            Defaults to settings.logging.format.
        log_file: Optional file path for log output.
            Defaults to settings.logging.file.
    """
    log_level = (level or settings.logging.level).upper()
    log_format = format or settings.logging.format
    file_path = log_file or settings.logging.file

    # Configure standard library logging
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, log_level))
        handlers.append(file_handler)

    logging.basicConfig(
        format='%(message)s',
        level=getattr(logging, log_level),
        handlers=handlers,
        force=True,
    )

    # Shared processors for all formats
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_timestamp,
        add_service_info,
        structlog.stdlib.ExtraAdder(),
    ]

    # Format-specific processors
    if log_format == 'json':
        # JSON output for production/log aggregation
        final_processors: list[Any] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console output for development
        final_processors = [
            *shared_processors,
            structlog.dev.ConsoleColors(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=final_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class ContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context attributes if not present."""
        if not hasattr(record, 'request_id'):
            record.request_id = '-'  # type: ignore
        if not hasattr(record, 'user_id'):
            record.user_id = '-'  # type: ignore
        return True


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name, typically __name__. If None, uses calling module.

    Returns:
        BoundLogger: Configured structlog logger with context support.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing complete", records_processed=1000)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log entries.

    Useful for adding consistent context like request_id, user_id, etc.

    Args:
        **kwargs: Key-value pairs to bind to logging context.

    Example:
        >>> bind_context(request_id="req-123", user_id="user-456")
        >>> logger.info("Operation started")  # Includes request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# Initialize logging on module import
configure_logging()

__all__ = [
    'ContextFilter',
    'add_service_info',
    'add_timestamp',
    'bind_context',
    'clear_context',
    'configure_logging',
    'get_logger',
]
