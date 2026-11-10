"""Shared fixtures.

Settings come from `server.settings_test`, which installs a hermetic config: every
adapter is `simulated`, so no test can reach the network.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from django.core.cache import cache
from django.test import Client

if TYPE_CHECKING:
    # Only django-stubs defines this name: the test client's response, with `.json()`.
    from django.test.client import _MonkeyPatchedWSGIResponse as TestResponse

type Rpc = Callable[..., TestResponse]


@pytest.fixture(autouse=True)
def _fresh_cache() -> Iterator[None]:
    """Forecasts, routes and rate-limit counters live in the cache; no test sees another's."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def rpc(client: Client) -> Rpc:
    """`rpc("trips/plan", {...})` -> POST /rpc/trips/plan with a JSON body."""

    def call(path: str, body: Any = None, **headers: str) -> TestResponse:
        return client.post(
            f"/rpc/{path}",
            data=json.dumps({} if body is None else body),
            content_type="application/json",
            headers=headers,
        )

    return call


def soon(hours: float = 1) -> str:
    """An ISO departure time `hours` from now, on the minute."""
    at = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(hours=hours)
    return at.isoformat()


CHICAGO = {"lat": 41.8781, "lon": -87.6298, "label": "Chicago, Illinois"}
ATLANTA = {"lat": 33.749, "lon": -84.388, "label": "Atlanta, Georgia"}


def plan_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "origin": CHICAGO,
        "destination": ATLANTA,
        "departureAt": soon(),
        "loadLb": 35_000,
        "intervalMi": 25,
    }
    body.update(overrides)
    return body


def encode_polyline(coords: Sequence[tuple[float, float]], precision: int = 6) -> str:
    """The inverse of `common.geo.decode_polyline`, for building fake OSRM responses."""
    factor = 10**precision
    out: list[str] = []
    prev_lat = prev_lon = 0
    for lon, lat in coords:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for delta in (ilat - prev_lat, ilon - prev_lon):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                out.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            out.append(chr(value + 63))
        prev_lat, prev_lon = ilat, ilon
    return "".join(out)
