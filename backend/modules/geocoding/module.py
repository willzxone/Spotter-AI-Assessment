"""Geocoding: turns what the driver types into coordinates."""

from __future__ import annotations

from core.config import AdapterMode
from core.module import ModuleContext, ServerModule, Service
from modules.geocoding import service
from modules.geocoding.adapters import (
    GeocodingAdapter,
    OffGeocoder,
    PhotonGeocoder,
    SimulatedGeocoder,
)
from modules.geocoding.router import procedures


def _register(ctx: ModuleContext) -> None:
    mode = ctx.config.geocoding_mode
    adapter: GeocodingAdapter
    if mode is AdapterMode.LIVE:
        adapter = PhotonGeocoder(ctx.http, ctx.config.photon_url)
    elif mode is AdapterMode.SIMULATED:
        adapter = SimulatedGeocoder()
    else:
        adapter = OffGeocoder()
    service.configure(adapter, ctx.cache)
    ctx.logger.info("geocoding adapter: %s", adapter.source)


geocoding_module = ServerModule(
    name="geocoding",
    version="1.0.0",
    requires=frozenset({Service.CONFIG, Service.HTTP, Service.CACHE}),
    procedures=procedures,
    register=_register,
)
