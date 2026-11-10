"""Route options between two points: the provider's alternatives, topped up with detours."""

from __future__ import annotations

import itertools
import logging
import math
from collections.abc import Sequence
from dataclasses import asdict

from django.core.cache.backends.base import BaseCache

from common.geo import EARTH_RADIUS_M, LonLat, bearing_deg, destination, haversine_m, locate, simplify
from core.errors import AppError, ErrorCode, bad_request, service_disabled
from modules.routing.adapters import RoutingAdapter
from modules.routing.constants import (
    MAX_DETOUR_RATIO,
    MAX_OVERLAP,
    MIN_TRIP_M,
    OVERLAP_PROBES,
    OVERLAP_RADIUS_M,
    OVERLAP_SIMPLIFY_M,
    ROUTE_CACHE_TTL_S,
    ROUTE_COUNT,
    VIA_OFFSET_CAP_M,
    VIA_OFFSETS,
)
from modules.routing.dto import RoadRoute

log = logging.getLogger("app.routing")

_adapter: RoutingAdapter | None = None
_cache: BaseCache | None = None


def configure(adapter: RoutingAdapter, cache: BaseCache) -> None:
    global _adapter, _cache
    _adapter, _cache = adapter, cache


def source() -> str:
    return _adapter.source if _adapter else "off"


def plan(origin: LonLat, destination_: LonLat) -> list[RoadRoute]:
    """Up to ROUTE_COUNT distinct routes, fastest first. Fewer only if no more exist."""
    if _adapter is None or _cache is None:
        raise service_disabled("routing")
    if haversine_m(origin, destination_) < MIN_TRIP_M:
        raise bad_request("Origin and destination are the same place.")
    key = "routing:v1:{}:{:.4f},{:.4f};{:.4f},{:.4f}".format(_adapter.source, *origin, *destination_)
    cached = _cache.get(key)
    if cached is not None:
        return [_restore(item) for item in cached]

    routes = _distinct([], _adapter.routes((origin, destination_), alternatives=True))
    if not routes:
        raise bad_request("No drivable route connects these places.")
    if len(routes) < ROUTE_COUNT:
        routes = _add_detours(_adapter, origin, destination_, routes)
    routes.sort(key=lambda r: r.duration_s)
    _cache.set(key, [asdict(route) for route in routes], ROUTE_CACHE_TTL_S)
    return routes


def _add_detours(
    adapter: RoutingAdapter, origin: LonLat, destination_: LonLat, routes: list[RoadRoute]
) -> list[RoadRoute]:
    straight_m = haversine_m(origin, destination_)
    heading = bearing_deg(origin, destination_)
    midpoint = destination(origin, heading, straight_m / 2)
    fastest_s = min(r.duration_s for r in routes)
    for share in VIA_OFFSETS:
        if len(routes) >= ROUTE_COUNT:
            break
        offset = min(abs(share) * straight_m, VIA_OFFSET_CAP_M)
        via = destination(midpoint, heading + math.copysign(90.0, share), offset)
        try:
            candidates = adapter.routes((origin, via, destination_), alternatives=False)
        except AppError as exc:
            if exc.code is not ErrorCode.UPSTREAM_UNAVAILABLE:
                raise
            # The main answer is already in hand; a failed top-up should not lose it.
            log.warning("detour request failed, returning %d routes: %s", len(routes), exc.message)
            break
        fast_enough = [c for c in candidates if c.duration_s <= fastest_s * MAX_DETOUR_RATIO]
        routes = _distinct(routes, fast_enough)
    return routes


def _distinct(kept: list[RoadRoute], candidates: Sequence[RoadRoute]) -> list[RoadRoute]:
    """Add candidates that don't mostly retrace a route already kept."""
    kept = list(kept)
    for candidate in candidates:
        if len(kept) >= ROUTE_COUNT:
            break
        if all(_overlap(candidate, other) <= MAX_OVERLAP for other in kept):
            kept.append(candidate)
    return kept


def _overlap(a: RoadRoute, b: RoadRoute) -> float:
    """Share of `a` that runs within OVERLAP_RADIUS_M of `b`."""
    line = [b.coords[i] for i in simplify(b.coords, OVERLAP_SIMPLIFY_M)]
    mean_lat = math.radians(sum(lat for _, lat in line) / len(line))
    kx = math.cos(mean_lat) * math.pi / 180 * EARTH_RADIUS_M
    ky = math.pi / 180 * EARTH_RADIUS_M
    xy = [(lon * kx, lat * ky) for lon, lat in line]
    shared = 0
    for i in range(OVERLAP_PROBES):
        at = a.distance_m * (i + 0.5) / OVERLAP_PROBES
        lon, lat = locate(a.coords, a.cumulative_m, at).coord
        if _distance_to_line((lon * kx, lat * ky), xy) <= OVERLAP_RADIUS_M:
            shared += 1
    return shared / OVERLAP_PROBES


def _distance_to_line(p: tuple[float, float], line: Sequence[tuple[float, float]]) -> float:
    px, py = p
    best = math.inf
    for (ax, ay), (bx, by) in itertools.pairwise(line):
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
        best = min(best, math.hypot(px - ax - t * dx, py - ay - t * dy))
    return best


def _restore(item: dict[str, object]) -> RoadRoute:
    return RoadRoute(
        summary=str(item["summary"]),
        coords=tuple(tuple(c) for c in item["coords"]),  # type: ignore[attr-defined]
        cumulative_m=tuple(item["cumulative_m"]),  # type: ignore[arg-type]
        cumulative_s=tuple(item["cumulative_s"]),  # type: ignore[arg-type]
    )
