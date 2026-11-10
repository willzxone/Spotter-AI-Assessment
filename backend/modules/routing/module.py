"""Routing: drivable route options between two points. Service-only; trips calls it."""

from __future__ import annotations

from core.config import AdapterMode
from core.module import ModuleContext, ServerModule, Service
from modules.routing import service
from modules.routing.adapters import OffRouter, OsrmRouter, RoutingAdapter, SimulatedRouter


def _register(ctx: ModuleContext) -> None:
    mode = ctx.config.routing_mode
    adapter: RoutingAdapter
    if mode is AdapterMode.LIVE:
        adapter = OsrmRouter(ctx.http, ctx.config.osrm_url)
    elif mode is AdapterMode.SIMULATED:
        adapter = SimulatedRouter()
    else:
        adapter = OffRouter()
    service.configure(adapter, ctx.cache)
    ctx.logger.info("routing adapter: %s", adapter.source)


routing_module = ServerModule(
    name="routing",
    version="1.0.0",
    requires=frozenset({Service.CONFIG, Service.HTTP, Service.CACHE}),
    register=_register,
)
