"""Global HTTP middleware owned by core."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from core.logging import bind_request_id, get_logger, reset_request_id

_REQUEST_ID_HEADER = "X-Request-Id"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_access_log = get_logger("http")


class RequestIdMiddleware:
    """Correlates logs per request and echoes the id back in `X-Request-Id`.

    An inbound id from a proxy is honoured only if it looks like an id, so a client
    cannot inject arbitrary text into the logs.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        inbound = request.headers.get(_REQUEST_ID_HEADER, "")
        request_id = inbound if _VALID_REQUEST_ID.match(inbound) else uuid.uuid4().hex
        token = bind_request_id(request_id)
        started = time.perf_counter()
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)
        response[_REQUEST_ID_HEADER] = request_id
        if request.path.startswith("/rpc/"):
            elapsed_ms = (time.perf_counter() - started) * 1000
            _access_log.info(
                "%s %s -> %s in %.0fms [%s]",
                request.method,
                request.path,
                response.status_code,
                elapsed_ms,
                request_id,
            )
        return response
