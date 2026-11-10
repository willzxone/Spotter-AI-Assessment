"""The single API handler.

One NinjaAPI is mounted at `/rpc/`; every booted module that has procedures gets
its router mounted at `/rpc/<module>/`. Every failure — a domain `AppError`, a
validation failure, a rate limit, or an unexpected crash — leaves as the same
envelope, so the frontend has exactly one error shape to handle:

    {"error": {"code": "...", "message": "...", "data": {...}, "requestId": "..."}}
"""

from __future__ import annotations

import functools
from typing import Any

from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI
from ninja.errors import HttpError, Throttled, ValidationError

from core import kernel
from core.config import get_config
from core.errors import HTTP_STATUS, AppError, ErrorCode
from core.logging import current_request_id, get_logger
from core.module import ServerModule

log = get_logger("api")

# HTTP statuses Ninja may raise on its own (bad JSON, wrong method) mapped onto our codes.
_HTTP_ERROR_CODES: dict[int, ErrorCode] = {
    400: ErrorCode.BAD_REQUEST,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.BAD_REQUEST,
    422: ErrorCode.VALIDATION_FAILED,
    429: ErrorCode.RATE_LIMITED,
}


def error_body(code: ErrorCode, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code.value,
            "message": message,
            "data": data or {},
            "requestId": current_request_id(),
        }
    }


def _issues(errors: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Flatten Ninja's validation errors into `{path, message}` pairs.

    Ninja reports locations like `("body", "payload", "origin", "lat")`; the first
    two entries are transport detail, so the path the client sees is `origin.lat`.
    """
    issues = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ())]
        if loc[:1] == ["body"]:
            loc = loc[2:]
        issues.append({"path": ".".join(loc), "message": str(error.get("msg", "Invalid value"))})
    return issues


def build_api(modules: tuple[ServerModule, ...], *, debug: bool) -> NinjaAPI:
    api = NinjaAPI(
        title="Weather-Aware Truck Routing",
        version="1.0.0",
        description="RPC API: every procedure is `POST /rpc/<module>/<procedure>` with a JSON body.",
        urls_namespace="rpc",
        docs_url="/docs" if debug else None,
        openapi_url="/openapi.json",
    )

    def respond(
        request: HttpRequest, code: ErrorCode, message: str, data: dict[str, Any] | None = None
    ) -> HttpResponse:
        return api.create_response(request, error_body(code, message, data), status=HTTP_STATUS[code])

    @api.exception_handler(AppError)
    def on_app_error(request: HttpRequest, exc: AppError) -> HttpResponse:
        if exc.status >= 500:
            log.warning("%s: %s", exc.code, exc.message)
        return respond(request, exc.code, exc.message, exc.data)

    @api.exception_handler(ValidationError)
    def on_validation_error(request: HttpRequest, exc: ValidationError) -> HttpResponse:
        issues = _issues(exc.errors)
        message = issues[0]["message"] if len(issues) == 1 else "The request has invalid fields"
        return respond(request, ErrorCode.VALIDATION_FAILED, message, {"issues": issues})

    @api.exception_handler(Throttled)
    def on_throttled(request: HttpRequest, exc: Throttled) -> HttpResponse:
        wait = int(exc.wait or 1)
        response = respond(
            request,
            ErrorCode.RATE_LIMITED,
            f"Too many requests — try again in {wait}s",
            {"retryAfterS": wait},
        )
        response["Retry-After"] = str(wait)
        return response

    @api.exception_handler(HttpError)
    def on_http_error(request: HttpRequest, exc: HttpError) -> HttpResponse:
        code = _HTTP_ERROR_CODES.get(exc.status_code, ErrorCode.BAD_REQUEST)
        return respond(request, code, str(exc))

    @api.exception_handler(Exception)
    def on_unexpected(request: HttpRequest, exc: Exception) -> HttpResponse:
        log.exception("unhandled error in %s", request.path)
        # Never leak internals; the request id in the body ties the user's report to the log line.
        return respond(request, ErrorCode.INTERNAL, "Something went wrong on our side")

    for module in modules:
        if module.procedures is not None:
            if module.procedures.module != module.name:
                raise RuntimeError(
                    f"Module {module.name!r} exposes procedures named {module.procedures.module!r}"
                )
            api.add_router(f"/{module.name}/", module.procedures.router)

    return api


@functools.cache
def get_api() -> NinjaAPI:
    """The process's one API, over the booted modules.

    Always go through this rather than calling `build_api` again: Ninja points every
    operation at the API that mounted it last, so a second instance would silently take
    over the live routes and their error handlers.
    """
    return build_api(kernel.boot(), debug=get_config().debug)
