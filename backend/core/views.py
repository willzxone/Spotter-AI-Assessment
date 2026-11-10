"""Plain Django views that sit outside the RPC surface: probes and the SPA shell."""

from __future__ import annotations

from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.http.response import HttpResponseBase
from django.views.decorators.http import require_GET

from core import kernel
from core.api import error_body
from core.config import get_config
from core.errors import ErrorCode


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness: the process is up and serving requests."""
    return JsonResponse({"status": "ok"})


@require_GET
def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness: every module has booted. Upstream providers are not probed here —
    a flaky third party should degrade one request, not pull the instance out of rotation."""
    if not kernel.is_ready():
        return JsonResponse({"status": "booting"}, status=503)
    return JsonResponse({"status": "ready"})


def rpc_not_found(request: HttpRequest, path: str = "") -> JsonResponse:
    """Unknown `/rpc/...` paths get the API envelope, not Django's HTML 404 page."""
    return JsonResponse(error_body(ErrorCode.NOT_FOUND, f"No procedure at /rpc/{path}"), status=404)


@require_GET
def spa(request: HttpRequest, path: str = "") -> HttpResponseBase:
    """Serve the built frontend's `index.html` for every client-side route.

    Hashed assets under `/assets/` are served by WhiteNoise before this view runs;
    anything that reaches here is a page the React router owns.
    """
    index = get_config().frontend_dist_dir / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Frontend not built. Run `pnpm build` in frontend/, or use the Vite dev server "
            "on http://localhost:3000 during development.",
            status=404,
            content_type="text/plain; charset=utf-8",
        )
    response = FileResponse(index.open("rb"), content_type="text/html; charset=utf-8")
    # The shell is tiny and references hashed assets; never let a stale one be cached.
    response["Cache-Control"] = "no-cache"
    return response
