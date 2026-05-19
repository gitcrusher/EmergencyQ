"""
app/utils/logger.py
====================
Centralized structured logger for the Emergency Complaint Analyzer backend.

Why this exists
---------------
Without this module, every file calls `logging.getLogger(__name__)` with
Python's default format. The result in production is inconsistent log lines
that are hard to parse, grep, or ship to Grafana Loki / CloudWatch.

This module provides:
  • A single `setup_logging()` call (invoked once at startup in main.py)
  • Consistent log format across all modules
  • A `get_logger()` factory used instead of logging.getLogger directly
  • Optional JSON output mode for log aggregation pipelines
  • Request-scoped correlation ID injection (for tracing API calls end-to-end)

Log format (human-readable, default):
    2025-05-10 14:23:01 | INFO  | app.routes.analyze | [req-abc123] Prediction: Fire (0.923)

Log format (JSON mode, LOG_FORMAT=json in .env):
    {"ts": "2025-05-10T14:23:01Z", "level": "INFO", "module": "app.routes.analyze",
     "req_id": "abc123", "msg": "Prediction: Fire (0.923)"}

Usage:
    # In main.py startup:
    from app.utils.logger import setup_logging
    setup_logging()

    # In any module (replaces logging.getLogger(__name__)):
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Prediction: %s (%.3f)", label, confidence)

    # To attach a request ID to the current async context:
    from app.utils.logger import set_request_id
    set_request_id("abc-123")
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

LOG_LEVEL:  str = os.environ.get("LOG_LEVEL",  "INFO").upper()
LOG_FORMAT: str = os.environ.get("LOG_FORMAT", "text")   # "text" | "json"

# ── Request-scoped correlation ID ─────────────────────────────────────────────
# Uses a ContextVar so each async request gets its own ID without thread-safety issues

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(req_id: str) -> None:
    """Set the request ID for the current async context (call at route entry)."""
    _request_id_var.set(req_id)


def get_request_id() -> str:
    """Return the current request ID (or '-' if not set)."""
    return _request_id_var.get()


# ── Custom formatters ─────────────────────────────────────────────────────────

class _TextFormatter(logging.Formatter):
    """
    Human-readable format:
        2025-05-10 14:23:01 | INFO  | app.routes.analyze | [req-abc123] message
    """

    LEVEL_WIDTH = 8   # pad level name to fixed width

    def format(self, record: logging.LogRecord) -> str:
        ts  = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        lvl = record.levelname.ljust(self.LEVEL_WIDTH)
        req = get_request_id()
        msg = super().format(record)
        return f"{ts} | {lvl} | {record.name} | [{req}] {record.getMessage()}"


class _JsonFormatter(logging.Formatter):
    """
    JSON format for log aggregation (Grafana Loki, AWS CloudWatch, Datadog):
        {"ts":"...","level":"INFO","module":"...","req_id":"...","msg":"..."}
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":     datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level":  record.levelname,
            "module": record.name,
            "req_id": get_request_id(),
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


# ── Setup function ────────────────────────────────────────────────────────────

def setup_logging(
    level:  Optional[str] = None,
    format: Optional[str] = None,
) -> None:
    """
    Configure the root logger for the entire application.

    Call this ONCE at application startup (in the lifespan handler in main.py),
    before any other logging calls.

    Parameters
    ----------
    level  : str  Log level override ("DEBUG", "INFO", "WARNING", "ERROR").
                  Defaults to LOG_LEVEL env var (default "INFO").
    format : str  "text" or "json". Defaults to LOG_FORMAT env var.
    """
    log_level  = getattr(logging, (level  or LOG_LEVEL),  logging.INFO)
    log_format = (format or LOG_FORMAT).lower()

    formatter = _JsonFormatter() if log_format == "json" else _TextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any handlers that were added by earlier basicConfig calls
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers unless we're in DEBUG mode
    if log_level > logging.DEBUG:
        for noisy in ("transformers", "chromadb", "sentence_transformers", "httpx", "uvicorn.access"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialized: level=%s format=%s",
        logging.getLevelName(log_level),
        log_format,
    )


# ── Module-level factory ──────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a logger for the given module name.

    Drop-in replacement for `logging.getLogger(__name__)`.
    All loggers created via this function automatically pick up
    the formatter configured by setup_logging().

    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Model loaded.")
    """
    return logging.getLogger(name)