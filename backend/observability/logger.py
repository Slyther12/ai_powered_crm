"""
Structured logging with context-aware fields for observability.
Uses Python's built-in logging with JSON formatting for production
and human-readable output for development.
"""
import logging
import json
import time
import uuid
from datetime import datetime, timezone
from contextvars import ContextVar
from functools import wraps

from backend.config import LOG_LEVEL, LOG_FORMAT

# Context variable for request-scoped data
_request_id: ContextVar[str] = ContextVar("request_id", default="system")
_operation: ContextVar[str] = ContextVar("operation", default="")


def set_request_context(request_id: str = None, operation: str = ""):
    """Set context variables for the current request/operation."""
    _request_id.set(request_id or str(uuid.uuid4())[:8])
    _operation.set(operation)


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get("system"),
            "operation": _operation.get(""),
        }
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable colored formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        req_id = _request_id.get("system")
        op = _operation.get("")
        prefix = f"{color}{ts} [{record.levelname:>7}]{self.RESET}"
        ctx = f" [{req_id}]" if req_id != "system" else ""
        op_str = f" ({op})" if op else ""

        msg = f"{prefix}{ctx}{op_str} {record.getMessage()}"

        if hasattr(record, "extra_fields"):
            extras = " | ".join(f"{k}={v}" for k, v in record.extra_fields.items())
            msg += f" | {extras}"
        if record.exc_info and record.exc_info[0]:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(f"nexusolve.{name}")

    if not logger.handlers:
        handler = logging.StreamHandler()
        if LOG_FORMAT == "json":
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        logger.propagate = False

    return logger


def log_with_extras(logger: logging.Logger, level: str, message: str, **kwargs):
    """Log a message with extra structured fields."""
    record = logger.makeRecord(
        logger.name, getattr(logging, level.upper()),
        "(unknown)", 0, message, (), None
    )
    record.extra_fields = kwargs
    logger.handle(record)


def timed(logger_name: str = None, operation: str = None):
    """Decorator to measure and log function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = get_logger(logger_name or func.__module__)
            op = operation or func.__name__
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                log_with_extras(_logger, "INFO", f"{op} completed",
                                duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                log_with_extras(_logger, "ERROR", f"{op} failed: {e}",
                                duration_ms=duration_ms, error=str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = get_logger(logger_name or func.__module__)
            op = operation or func.__name__
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                log_with_extras(_logger, "INFO", f"{op} completed",
                                duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                log_with_extras(_logger, "ERROR", f"{op} failed: {e}",
                                duration_ms=duration_ms, error=str(e))
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
