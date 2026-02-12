"""
Structured JSON logging configuration for production
"""
import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.default_fields = kwargs

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add default fields
        log_data.update(self.default_fields)

        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint

        if hasattr(record, "method"):
            log_data["method"] = record.method

        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        if hasattr(record, "client_ip"):
            log_data["client_ip"] = record.client_ip

        # Add any other extra attributes
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "request_id", "user_id", "endpoint", "method",
                "status_code", "duration_ms", "client_ip"
            ) and not key.startswith("_"):
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for development
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build base message
        message = f"{timestamp} | {color}{record.levelname:8}{self.RESET} | {record.name} | {record.getMessage()}"

        # Add request_id if present
        if hasattr(record, "request_id") and record.request_id:
            message = f"{timestamp} | {color}{record.levelname:8}{self.RESET} | [{record.request_id[:8]}] | {record.name} | {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request context to log records
    """

    def __init__(self):
        super().__init__()
        self._context: Dict[str, Any] = {}

    def set_context(self, **kwargs):
        """Set context values for current request"""
        self._context.update(kwargs)

    def clear_context(self):
        """Clear context after request"""
        self._context.clear()

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self._context.items():
            setattr(record, key, value)
        return True


# Global context filter instance
context_filter = RequestContextFilter()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    json_logs: Optional[bool] = None
):
    """
    Configure application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_logs: Force JSON logging (None = auto based on DEBUG setting)
    """
    # Determine if we should use JSON logging
    use_json = json_logs if json_logs is not None else not settings.DEBUG

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if use_json:
        console_handler.setFormatter(JSONFormatter(
            service=settings.PROJECT_NAME,
            environment=getattr(settings, 'SENTRY_ENVIRONMENT', 'development')
        ))
    else:
        console_handler.setFormatter(ConsoleFormatter())
    handlers.append(console_handler)

    # File handler (always JSON for parsing)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter(
            service=settings.PROJECT_NAME,
            environment=getattr(settings, 'SENTRY_ENVIRONMENT', 'development')
        ))
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers with context filter
    for handler in handlers:
        handler.addFilter(context_filter)
        root_logger.addHandler(handler)

    # Set logging level for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiosmtplib").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggingContextManager:
    """
    Context manager for adding request context to logs
    """

    def __init__(self, **kwargs):
        self.context = kwargs

    def __enter__(self):
        context_filter.set_context(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        context_filter.clear_context()
        return False


def log_with_context(**kwargs):
    """
    Decorator/context manager for adding context to logs

    Usage:
        with log_with_context(request_id="abc123", user_id=42):
            logger.info("Processing request")
    """
    return LoggingContextManager(**kwargs)
