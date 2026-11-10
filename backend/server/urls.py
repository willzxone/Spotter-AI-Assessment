"""URL map. `/rpc/` is the API; probes sit beside it; everything else is the SPA shell."""

from __future__ import annotations

from django.urls import path, re_path

from core import views
from core.api import get_api

# `get_api` boots the modules first (as AppConfig.ready also does; `boot` is idempotent), so
# they are configured before their routers are mounted, whichever Django imports first.
urlpatterns = [
    path("healthz", views.healthz),
    path("readyz", views.readyz),
    path("rpc/", get_api().urls),
    # Unknown procedures under /rpc/ get the API's error envelope, not the SPA shell.
    re_path(r"^rpc/(?P<path>.*)$", views.rpc_not_found),
    re_path(r"^(?P<path>.*)$", views.spa),
]
