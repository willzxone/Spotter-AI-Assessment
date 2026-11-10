"""Domain errors.

Modules raise `AppError` through the helpers below — never a bare `Exception` and
never an HTTP response. `core.api` maps each code to an HTTP status and a uniform
JSON body: {"error": {"code", "message", "data", "requestId"}}.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    SERVICE_DISABLED = "SERVICE_DISABLED"
    INTERNAL = "INTERNAL"


HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.VALIDATION_FAILED: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.UPSTREAM_UNAVAILABLE: 502,
    ErrorCode.SERVICE_DISABLED: 503,
    ErrorCode.INTERNAL: 500,
}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}

    @property
    def status(self) -> int:
        return HTTP_STATUS[self.code]


def bad_request(message: str, **data: Any) -> AppError:
    return AppError(ErrorCode.BAD_REQUEST, message, data=data)


def not_found(what: str, **data: Any) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, f"{what} not found", data=data)


def rate_limited(retry_after_s: int, *, scope: str) -> AppError:
    return AppError(
        ErrorCode.RATE_LIMITED,
        f"Too many requests — try again in {retry_after_s}s",
        data={"retryAfterS": retry_after_s, "scope": scope},
    )


def upstream_unavailable(service: str, detail: str) -> AppError:
    return AppError(
        ErrorCode.UPSTREAM_UNAVAILABLE,
        f"The {service} provider is unavailable: {detail}",
        data={"service": service},
    )


def service_disabled(service: str) -> AppError:
    return AppError(
        ErrorCode.SERVICE_DISABLED,
        f"The {service} service is turned off on this server",
        data={"service": service},
    )
