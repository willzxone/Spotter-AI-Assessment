"""The live adapters against canned provider responses (httpx.MockTransport, no network)."""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from common.geo import cumulative_distances, destination
from core.errors import AppError, ErrorCode
from modules.geocoding.adapters import PhotonGeocoder
from modules.routing.adapters import OsrmRouter
from modules.weather.adapters import OpenMeteoWeather
from modules.weather.constants import BATCH_SIZE
from tests.conftest import encode_polyline

Handler = Callable[[httpx.Request], httpx.Response]


def client(handler: Handler, seen: list[httpx.Request] | None = None) -> httpx.Client:
    def record(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(record))


def reply(body: Any, status: int = 200) -> Handler:
    return lambda _request: httpx.Response(status, json=body)


def assert_upstream(exc: pytest.ExceptionInfo[AppError], detail: str) -> None:
    assert exc.value.code is ErrorCode.UPSTREAM_UNAVAILABLE
    assert detail in exc.value.message


# ---- OSRM ------------------------------------------------------------------------------------

ORIGIN = (-87.6298, 41.8781)
DEST = (-84.388, 33.749)


def osrm_route(
    coords: list[tuple[float, float]], summaries: list[str], *, annotate: bool = True
) -> dict[str, Any]:
    """One OSRM route with one leg per summary, the geometry split evenly between legs."""
    cumulative = cumulative_distances(coords)
    seg_m = [b - a for a, b in itertools.pairwise(cumulative)]
    seg_s = [d / 25.0 for d in seg_m]
    per_leg = len(seg_m) // len(summaries)
    legs = []
    for i, summary in enumerate(summaries):
        lo = i * per_leg
        hi = len(seg_m) if i == len(summaries) - 1 else lo + per_leg
        annotation = (
            {"distance": seg_m[lo:hi], "duration": seg_s[lo:hi]}
            if annotate
            else {"distance": [1.0], "duration": [1.0]}
        )
        legs.append({"summary": summary, "annotation": annotation})
    return {
        "geometry": encode_polyline(coords),
        "distance": cumulative[-1],
        "duration": cumulative[-1] / 25.0,
        "legs": legs,
    }


def line(n: int = 20) -> list[tuple[float, float]]:
    return [
        (round(lon, 6), round(lat, 6))
        for lon, lat in (destination(ORIGIN, 160, k * 40_000) for k in range(n))
    ]


def test_osrm_request_shape() -> None:
    seen: list[httpx.Request] = []
    router = OsrmRouter(client(reply({"code": "Ok", "routes": []}), seen), "https://osrm.test/")
    router.routes([ORIGIN, DEST], alternatives=True)

    (request,) = seen
    assert request.url.path == "/route/v1/driving/-87.629800,41.878100;-84.388000,33.749000"
    assert dict(request.url.params) == {
        "alternatives": "3",
        "overview": "full",
        "geometries": "polyline6",
        "annotations": "distance,duration",
        "steps": "true",
    }


def test_osrm_parses_geometry_timing_and_summary() -> None:
    coords = line()
    body = {"code": "Ok", "routes": [osrm_route(coords, ["I 65, I 75", "I 75; I 24, I 85"])]}
    (route,) = OsrmRouter(client(reply(body)), "https://osrm.test").routes([ORIGIN, DEST], alternatives=True)

    assert route.coords == tuple(coords)
    assert route.cumulative_m[0] == 0
    assert route.distance_m == pytest.approx(cumulative_distances(coords)[-1])
    assert route.duration_s == pytest.approx(route.distance_m / 25.0)
    assert route.summary == "I 65, I 75, I 24, I 85"


def test_osrm_spreads_totals_when_annotations_do_not_match_the_geometry() -> None:
    coords = line()
    raw = osrm_route(coords, ["I 65"], annotate=False)
    raw["distance"], raw["duration"] = 900_000.0, 36_000.0
    (route,) = OsrmRouter(client(reply({"code": "Ok", "routes": [raw]})), "https://osrm.test").routes(
        [ORIGIN, DEST], alternatives=True
    )
    assert len(route.cumulative_m) == len(coords)
    assert route.distance_m == pytest.approx(900_000)
    assert route.duration_s == pytest.approx(36_000)


@pytest.mark.parametrize("code", ["NoRoute", "NoSegment"])
def test_osrm_no_route_is_an_empty_answer(code: str) -> None:
    router = OsrmRouter(client(reply({"code": code, "message": "x"}, status=400)), "https://osrm.test")
    assert router.routes([ORIGIN, DEST], alternatives=True) == []


@pytest.mark.parametrize(
    ("handler", "detail"),
    [
        (reply({"message": "slow down"}, status=429), "rate limiting"),
        (reply({"code": "InvalidQuery"}, status=400), "provider answered InvalidQuery"),
        (reply({}, status=502), "provider answered 502"),
        (lambda _r: httpx.Response(200, content=b"<html>"), "unreadable response"),
        (reply({"code": "Ok", "routes": [{"geometry": "??"}]}), "unreadable response"),
    ],
)
def test_osrm_failures_are_upstream_unavailable(handler: Handler, detail: str) -> None:
    with pytest.raises(AppError) as exc:
        OsrmRouter(client(handler), "https://osrm.test").routes([ORIGIN, DEST], alternatives=True)
    assert_upstream(exc, detail)


def test_osrm_transport_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(AppError) as exc:
        OsrmRouter(client(boom), "https://osrm.test").routes([ORIGIN, DEST], alternatives=True)
    assert_upstream(exc, "ConnectTimeout")


# ---- Open-Meteo ------------------------------------------------------------------------------

START = datetime(2026, 11, 10, 14, tzinfo=UTC)


def meteo_item(
    hours: int, *, wind: float = 10, rain: float | None = 0.1, showers: float = 0.05
) -> dict[str, Any]:
    n = hours + 1
    return {
        "hourly": {
            "time": list(range(n)),
            "wind_speed_10m": [wind] * n,
            "wind_gusts_10m": [wind * 1.5] * n,
            "rain": [rain] * n,
            "showers": [showers] * n,
            "snowfall": [0.0] * n,
        }
    }


def test_open_meteo_request_shape_and_parsing() -> None:
    seen: list[httpx.Request] = []
    cells = [(-87.625, 41.875), (-84.375, 33.625)]
    body = [meteo_item(3, wind=12), meteo_item(3, wind=40)]
    weather = OpenMeteoWeather(client(reply(body), seen), "https://meteo.test/", api_key=None)
    series = weather.hourly(cells, START, 3)

    (request,) = seen
    assert request.url.path == "/v1/forecast"
    params = dict(request.url.params)
    assert params["latitude"] == "41.8750,33.6250"
    assert params["longitude"] == "-87.6250,-84.3750"
    assert params["hourly"] == "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
    assert params["wind_speed_unit"] == "mph"
    assert params["precipitation_unit"] == "inch"
    assert params["start_hour"] == "2026-11-10T14:00"
    assert params["end_hour"] == "2026-11-10T17:00"
    assert "apikey" not in params

    assert [len(s) for s in series] == [4, 4]
    assert series[0].wind_mph[0] == 12
    assert series[1].wind_mph[0] == 40
    assert series[0].rain_in_hr[0] == pytest.approx(0.15)  # rain + convective showers


def test_open_meteo_a_single_location_answer_is_an_object_and_gaps_are_zero() -> None:
    body = meteo_item(2, rain=None, showers=0.0)
    (series,) = OpenMeteoWeather(client(reply(body)), "https://meteo.test", api_key=None).hourly(
        [(-87.625, 41.875)], START, 2
    )
    assert series.rain_in_hr == (0.0, 0.0, 0.0)


def test_open_meteo_batches_and_sends_the_customer_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        count = len(request.url.params["latitude"].split(","))
        return httpx.Response(200, json=[meteo_item(1)] * count)

    cells = [(-100 + i * 0.25, 40.0) for i in range(BATCH_SIZE + 5)]
    series = OpenMeteoWeather(client(handler, seen), "https://customer-api.meteo.test", api_key="k").hourly(
        cells, START, 1
    )
    assert len(series) == len(cells)
    assert [len(r.url.params["latitude"].split(",")) for r in seen] == [BATCH_SIZE, 5]
    assert all(r.url.params["apikey"] == "k" for r in seen)


@pytest.mark.parametrize(
    ("handler", "detail"),
    [
        (
            reply({"error": True, "reason": "Parameter 'start_hour' is out of range"}, status=400),
            "start_hour",
        ),
        (reply({}, status=429), "rate limiting"),
        (reply([meteo_item(3)]), "wrong number of locations"),  # asked for two
        (reply([meteo_item(1), meteo_item(1)]), "unreadable response"),  # too few hours
    ],
)
def test_open_meteo_failures_are_upstream_unavailable(handler: Handler, detail: str) -> None:
    with pytest.raises(AppError) as exc:
        OpenMeteoWeather(client(handler), "https://meteo.test", api_key=None).hourly(
            [(-87.625, 41.875), (-84.375, 33.625)], START, 3
        )
    assert_upstream(exc, detail)


# ---- Photon ----------------------------------------------------------------------------------


def feature(lon: float, lat: float, **props: Any) -> dict[str, Any]:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}


def test_photon_request_and_places() -> None:
    seen: list[httpx.Request] = []
    body = {
        "features": [
            feature(
                -87.62,
                41.87,
                osm_type="R",
                osm_id=122604,
                name="Chicago",
                state="Illinois",
                country="United States",
                type="city",
            ),
            # Same label again (Photon returns node + relation for many cities): dropped.
            feature(
                -87.63,
                41.88,
                osm_type="N",
                osm_id=1,
                name="Chicago",
                state="Illinois",
                country="United States",
                type="city",
            ),
            feature(
                -87.6,
                41.9,
                osm_type="W",
                osm_id=7,
                street="Michigan Avenue",
                housenumber="233",
                city="Chicago",
                state="Illinois",
                country="United States",
                osm_value="house",
            ),
            feature(-87.6, 41.9, osm_type="N", osm_id=9),  # nothing to call it: dropped
            {"type": "Feature", "geometry": None, "properties": {"name": "Broken"}},  # no geometry: dropped
        ]
    }
    places = PhotonGeocoder(client(reply(body), seen), "https://photon.test/").search("chicago", 5)

    (request,) = seen
    assert request.url.path == "/api"
    assert dict(request.url.params) == {"q": "chicago", "limit": "5", "lang": "en"}

    assert [(p.id, p.name, p.label, p.kind) for p in places] == [
        ("R122604", "Chicago", "Chicago, Illinois, United States", "city"),
        ("W7", "233 Michigan Avenue", "233 Michigan Avenue, Chicago, Illinois, United States", "house"),
    ]
    assert (places[0].lat, places[0].lon) == (41.87, -87.62)


@pytest.mark.parametrize(
    ("handler", "detail"),
    [
        (reply({}, status=429), "rate limiting"),
        (reply({}, status=500), "HTTP 500"),
        (lambda _r: httpx.Response(200, content=json.dumps([1]).encode()[:1]), "unreadable response"),
    ],
)
def test_photon_failures_are_upstream_unavailable(handler: Handler, detail: str) -> None:
    with pytest.raises(AppError) as exc:
        PhotonGeocoder(client(handler), "https://photon.test").search("chicago", 5)
    assert_upstream(exc, detail)
