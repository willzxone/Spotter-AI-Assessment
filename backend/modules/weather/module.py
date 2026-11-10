"""Weather: hourly forecasts along the corridor. Service-only; trips calls it."""

from __future__ import annotations

from core.config import AdapterMode
from core.module import ModuleContext, ServerModule, Service
from modules.weather import service
from modules.weather.adapters import OffWeather, OpenMeteoWeather, SimulatedWeather, WeatherAdapter


def _register(ctx: ModuleContext) -> None:
    config = ctx.config
    adapter: WeatherAdapter
    if config.weather_mode is AdapterMode.LIVE:
        adapter = OpenMeteoWeather(ctx.http, config.open_meteo_url, config.open_meteo_api_key)
    elif config.weather_mode is AdapterMode.SIMULATED:
        adapter = SimulatedWeather()
    else:
        adapter = OffWeather()
    service.configure(adapter, ctx.cache, config.weather_cache_ttl_s)
    ctx.logger.info("weather adapter: %s", adapter.source)


weather_module = ServerModule(
    name="weather",
    version="1.0.0",
    requires=frozenset({Service.CONFIG, Service.HTTP, Service.CACHE}),
    register=_register,
)
