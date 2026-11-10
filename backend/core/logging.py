"""Logging setup and request correlation.

Every log line carries the request id of the request that produced it (or "-"
outside a request). Modules receive a child logger from the kernel; nothing else
configures handlers.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

ROOT_LOGGER = "app"


def current_request_id() -> str:
    return _request_id.get()


def bind_request_id(request_id: str) -> object:
    """Bind a request id for the current context; returns a token for `reset_request_id`."""
    return _request_id.set(request_id)


def reset_request_id(token: object) -> None:
    _request_id.reset(token)  # type: ignore[arg-type]


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def get_logger(name: str) -> logging.Logger:
    """A logger under the application root, e.g. `app.weather`."""
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")


def logging_config(level: str) -> dict[str, Any]:
    """`LOGGING` dict for Django settings."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id": {"()": "core.logging.RequestIdFilter"}},
        "formatters": {
            "line": {
                "format": "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "line",
                "filters": ["request_id"],
            }
        },
        "loggers": {
            ROOT_LOGGER: {"handlers": ["console"], "level": level, "propagate": False},
            "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        },
    }
