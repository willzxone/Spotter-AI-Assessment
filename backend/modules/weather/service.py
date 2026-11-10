"""Hourly forecasts for grid cells, cached per cell and forecast window."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict
from datetime import datetime

from django.core.cache.backends.base import BaseCache

from common.geo import LonLat, snap
from core.errors import service_disabled
from modules.weather.adapters import WeatherAdapter
from modules.weather.constants import CELL_DEG
from modules.weather.dto import HourlySeries

_adapter: WeatherAdapter | None = None
_cache: BaseCache | None = None
_ttl_s = 900


def configure(adapter: WeatherAdapter, cache: BaseCache, ttl_s: int) -> None:
    global _adapter, _cache, _ttl_s
    _adapter, _cache, _ttl_s = adapter, cache, ttl_s


def source() -> str:
    return _adapter.source if _adapter else "off"


def cell_of(coord: LonLat) -> LonLat:
    """The grid cell whose forecast stands in for `coord`."""
    return snap(coord, CELL_DEG)


def forecast(cells: Iterable[LonLat], start: datetime, hours: int) -> dict[LonLat, HourlySeries]:
    """`hours + 1` hourly values per cell from `start`, which must be a whole UTC hour."""
    if _adapter is None or _cache is None:
        raise service_disabled("weather")
    wanted = sorted(set(cells))
    window = f"{start:%Y%m%dT%H}:{hours}"
    keys = {cell: f"weather:v1:{_adapter.source}:{cell[0]:.2f},{cell[1]:.2f}:{window}" for cell in wanted}
    hits = _cache.get_many(list(keys.values()))
    out: dict[LonLat, HourlySeries] = {}
    missing: list[LonLat] = []
    for cell in wanted:
        cached = hits.get(keys[cell])
        if cached is None:
            missing.append(cell)
        else:
            out[cell] = _restore(cached)
    if missing:
        fetched = _adapter.hourly(missing, start, hours)
        _cache.set_many({keys[c]: asdict(s) for c, s in zip(missing, fetched, strict=True)}, _ttl_s)
        out.update(zip(missing, fetched, strict=True))
    return out


def _restore(item: dict[str, Sequence[float]]) -> HourlySeries:
    return HourlySeries(
        wind_mph=tuple(item["wind_mph"]),
        gust_mph=tuple(item["gust_mph"]),
        rain_in_hr=tuple(item["rain_in_hr"]),
        snow_in_hr=tuple(item["snow_in_hr"]),
    )
