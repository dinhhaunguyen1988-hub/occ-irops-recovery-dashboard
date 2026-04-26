"""Structured JSON logging for OCC IROPS Recovery Dashboard.

Emits one JSON object per log record to stdout. Keeps dependencies to the
standard library only — keeps deployment simple and Docker logs trivially
shippable to Loki/Datadog/CloudWatch.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

_RESERVED_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Format LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_KEYS or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with a single JSON stdout handler.

    Idempotent — safe to call multiple times (Streamlit re-runs the script
    on every interaction).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (level or os.environ.get("OCC_LOG_LEVEL") or "INFO").upper()
    log_level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Caller is responsible for calling setup_logging."""
    return logging.getLogger(name)
