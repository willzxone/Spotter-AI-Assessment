"""Module services with fake adapters: caching, the detour top-up and its failure modes."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from django.core.cache import cache

from common.geo import LonLat
from core.errors import AppError, ErrorCode, upstream_unavailable
from modules.routing import service as routing
from modules.routing.adapters import SimulatedRouter
from modules.routing.constants import ROUTE_COUNT
from modules.routing.dto import RoadRoute
from modules.weather import service as weather
from modules.weather.adapters import SimulatedWeather
from modules.weather.dto import HourlySeries

CHICAGO: LonLat = (-87.6298, 41.8781)
ATLANTA: LonLat = (-84.388, 33.749)


class OneAlternativeRouter:
    """Like OSRM on a quiet day: one route when asked for alternatives, detours on request."""

    source = "fake"

    def __init__(self, *, detour_error: AppError | None = None, detour_speedup: float = 1.0) -> None:
        self.inner = SimulatedRouter()
        self.calls: list[tuple[int, bool]] = []
        self.detour_error = detour_error
        self.detour_speedup = detour_speedup

    def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
        self.calls.append((len(waypoints), alternatives))
        if alternatives:
            return self.inner.routes(waypoints, alternatives=True)[:1]
        if self.detour_error is not None:
            raise self.detour_error
        (route,) = self.inner.routes(waypoints, alternatives=False)
        return [
            RoadRoute(
                summary=route.summary,
                coords=route.coords,
                cumulative_m=route.cumulative_m,
                cumulative_s=tuple(s / self.detour_speedup for s in route.cumulative_s),
            )
        ]


@pytest.fixture
def use_router(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    def install(adapter: object) -> None:
        monkeypatch.setattr(routing, "_adapter", adapter)
        monkeypatch.setattr(routing, "_cache", cache)

    return install


def test_simulated_router_gives_three_distinct_routes_fastest_first(use_router) -> None:  # type: ignore[no-untyped-def]
    use_router(SimulatedRouter())
    routes = routing.plan(CHICAGO, ATLANTA)
    assert len(routes) == ROUTE_COUNT
    durations = [r.duration_s for r in routes]
    assert durations == sorted(durations)


def test_detours_top_up_a_single_alternative(use_router) -> None:  # type: ignore[no-untyped-def]
    router = OneAlternativeRouter()
    use_router(router)
    routes = routing.plan(CHICAGO, ATLANTA)

    assert len(routes) == ROUTE_COUNT
    assert router.calls[0] == (2, True)
    assert all(call == (3, False) for call in router.calls[1:])  # origin, via, destination
    for i, a in enumerate(routes):
        for b in routes[i + 1 :]:
            assert routing._overlap(a, b) <= 0.6


def test_detours_much_slower_than_the_fastest_route_are_dropped(use_router) -> None:  # type: ignore[no-untyped-def]
    use_router(OneAlternativeRouter(detour_speedup=0.2))  # every detour takes 5x as long
    assert len(routing.plan(CHICAGO, ATLANTA)) == 1


def test_a_failed_detour_keeps_the_main_answer(use_router) -> None:  # type: ignore[no-untyped-def]
    use_router(OneAlternativeRouter(detour_error=upstream_unavailable("routing", "rate limited")))
    assert len(routing.plan(CHICAGO, ATLANTA)) == 1


def test_routes_are_cached(use_router) -> None:  # type: ignore[no-untyped-def]
    router = OneAlternativeRouter()
    use_router(router)
    first = routing.plan(CHICAGO, ATLANTA)
    calls = len(router.calls)
    second = routing.plan(CHICAGO, ATLANTA)
    assert len(router.calls) == calls
    assert second == first


def test_same_place_and_no_route_are_bad_requests(use_router) -> None:  # type: ignore[no-untyped-def]
    class Nowhere:
        source = "fake"

        def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
            return []

    use_router(Nowhere())
    with pytest.raises(AppError) as same:
        routing.plan(CHICAGO, (CHICAGO[0] + 0.001, CHICAGO[1]))
    assert same.value.code is ErrorCode.BAD_REQUEST

    with pytest.raises(AppError) as none:
        routing.plan(CHICAGO, (-157.8583, 21.3069))  # Honolulu
    assert none.value.code is ErrorCode.BAD_REQUEST
    assert "No drivable route" in none.value.message


def test_weather_fetches_only_cells_it_has_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[list[LonLat]] = []

    class Counting(SimulatedWeather):
        def hourly(self, cells: Sequence[LonLat], start: datetime, hours: int) -> list[HourlySeries]:
            asked.append(list(cells))
            return super().hourly(cells, start, hours)

    monkeypatch.setattr(weather, "_adapter", Counting())
    monkeypatch.setattr(weather, "_cache", cache)
    start = datetime(2026, 11, 10, 14, tzinfo=UTC)
    a, b, c = (-87.625, 41.875), (-86.125, 39.875), (-84.375, 33.625)

    first = weather.forecast([a, b, a], start, 6)
    assert set(first) == {a, b}
    assert len(first[a]) == 7

    second = weather.forecast([a, b, c], start, 6)
    assert asked == [[a, b], [c]]
    assert second[a] == first[a]

    weather.forecast([a], start.replace(hour=15), 6)  # a different window is a different forecast
    assert len(asked) == 3


def test_services_refuse_when_their_adapter_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weather, "_adapter", None)
    with pytest.raises(AppError) as exc:
        weather.forecast([(-87.625, 41.875)], datetime(2026, 11, 10, tzinfo=UTC), 1)
    assert exc.value.code is ErrorCode.SERVICE_DISABLED
