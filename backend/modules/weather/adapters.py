"""Weather adapters: off, simulated (moving synthetic storms) and live (Open-Meteo)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, Protocol

import httpx

from common.geo import LonLat
from core.errors import service_disabled, upstream_unavailable
from modules.weather.constants import (
    BATCH_SIZE,
    HOURLY_VARIABLES,
    SIMULATED_BASE_WIND_MPH,
    SIMULATED_GUST_FACTOR,
    SIMULATED_SNOW_LAT,
    SIMULATED_STORMS,
)
from modules.weather.dto import HourlySeries


class WeatherAdapter(Protocol):
    source: str

    def hourly(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
        """`hours + 1` hourly values per cell from `start` (a whole UTC hour), in `cells` order."""
        ...


class OffWeather:
    source = "off"

    def hourly(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
        raise service_disabled("weather")


class SimulatedWeather:
    """Deterministic storms that drift east, so every risk level shows up offline."""

    source = "simulated"

    def hourly(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
        return [self._series(cell, hours) for cell in cells]

    def _series(self, cell: LonLat, hours: int) -> HourlySeries:
        lon, lat = cell
        wind: list[float] = []
        precip: list[float] = []
        for h in range(hours + 1):
            w, p = SIMULATED_BASE_WIND_MPH, 0.0
            for lon0, lat0, speed, radius, peak_wind, peak_precip in SIMULATED_STORMS:
                dx = (lon - (lon0 + speed * h)) * math.cos(math.radians(lat))
                dy = lat - lat0
                weight = math.exp(-(dx * dx + dy * dy) / (radius * radius))
                w += peak_wind * weight
                p += peak_precip * weight
            wind.append(round(w, 1))
            precip.append(round(p, 3))
        snowy = lat >= SIMULATED_SNOW_LAT
        zeros = (0.0,) * (hours + 1)
        return HourlySeries(
            wind_mph=tuple(wind),
            gust_mph=tuple(round(w * SIMULATED_GUST_FACTOR, 1) for w in wind),
            rain_in_hr=zeros if snowy else tuple(precip),
            snow_in_hr=tuple(precip) if snowy else zeros,
        )


class OpenMeteoWeather:
    """Open-Meteo forecast API. Free tier without a key; the customer endpoint takes `apikey`."""

    source = "open-meteo"

    def __init__(self, http: httpx.Client, base_url: str, api_key: str | None) -> None:
        self._http = http
        self._url = base_url.rstrip("/") + "/v1/forecast"
        self._api_key = api_key

    def hourly(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
        out: list[HourlySeries] = []
        for i in range(0, len(cells), BATCH_SIZE):
            out.extend(self._batch(cells[i : i + BATCH_SIZE], start, hours))
        return out

    def _batch(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
        end = start + timedelta(hours=hours)
        params = {
            "latitude": ",".join(f"{lat:.4f}" for _, lat in cells),
            "longitude": ",".join(f"{lon:.4f}" for lon, _ in cells),
            "hourly": ",".join(HOURLY_VARIABLES),
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timeformat": "unixtime",
            "timezone": "GMT",
            "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
            "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
        }
        if self._api_key:
            params["apikey"] = self._api_key
        try:
            response = self._http.get(self._url, params=params)
        except httpx.HTTPError as exc:
            raise upstream_unavailable("weather", type(exc).__name__) from exc
        if response.status_code == 429:
            raise upstream_unavailable("weather", "the provider is rate limiting us")
        try:
            body = response.json()
        except ValueError as exc:
            raise upstream_unavailable("weather", "unreadable response") from exc
        if response.status_code >= 400 or (isinstance(body, dict) and body.get("error")):
            reason = body.get("reason") if isinstance(body, dict) else None
            raise upstream_unavailable("weather", str(reason or f"provider answered {response.status_code}"))
        # One location answers with an object, several with a list in request order.
        items = body if isinstance(body, list) else [body]
        if len(items) != len(cells):
            raise upstream_unavailable("weather", "provider returned the wrong number of locations")
        try:
            return [_from_open_meteo(item["hourly"], hours) for item in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise upstream_unavailable("weather", "unreadable response") from exc


def _from_open_meteo(hourly: dict[str, Any], hours: int) -> HourlySeries:
    def column(name: str) -> list[float]:
        values = hourly[name]
        if len(values) != hours + 1:
            raise ValueError(f"{name}: expected {hours + 1} values, got {len(values)}")
        # A null is a gap in the model run; treat it as calm/dry rather than fail the whole trip.
        return [float(v) if v is not None else 0.0 for v in values]

    rain = column("rain")
    showers = column("showers")
    return HourlySeries(
        wind_mph=tuple(column("wind_speed_10m")),
        gust_mph=tuple(column("wind_gusts_10m")),
        # Hourly totals in inches are the hour's rate in in/hr. Showers are convective rain.
        rain_in_hr=tuple(r + s for r, s in zip(rain, showers, strict=True)),
        snow_in_hr=tuple(column("snowfall")),
    )
