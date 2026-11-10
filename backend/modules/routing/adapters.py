"""Routing adapters: off, simulated (synthetic offline routes) and live (OSRM)."""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from common.geo import LonLat, bearing_deg, cumulative_distances, decode_polyline, destination, haversine_m
from core.errors import service_disabled, upstream_unavailable
from modules.routing.constants import (
    SIMULATED_DETOUR_SPEED_MPS,
    SIMULATED_STEP_M,
    SIMULATED_VARIANTS,
)
from modules.routing.dto import RoadRoute


class RoutingAdapter(Protocol):
    source: str

    def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
        """Routes through `waypoints` in order. An empty list means no road connects them."""
        ...


class OffRouter:
    source = "off"

    def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
        raise service_disabled("routing")


class SimulatedRouter:
    """Deterministic synthetic routes: each leg is a great-circle line bowed sideways."""

    source = "simulated"

    def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
        if not alternatives:
            return [_synthetic("Simulated detour", waypoints, 0.0, SIMULATED_DETOUR_SPEED_MPS)]
        return [_synthetic(label, waypoints, bow, speed) for label, bow, speed in SIMULATED_VARIANTS]


def _synthetic(label: str, waypoints: Sequence[LonLat], bow: float, speed_mps: float) -> RoadRoute:
    coords: list[LonLat] = [waypoints[0]]
    for a, b in itertools.pairwise(waypoints):
        length = haversine_m(a, b)
        heading = bearing_deg(a, b)
        steps = max(2, math.ceil(length / SIMULATED_STEP_M))
        for i in range(1, steps + 1):
            t = i / steps
            point = destination(a, heading, t * length)
            offset = bow * length * math.sin(math.pi * t)
            if offset:
                point = destination(point, heading + 90.0, offset)
            coords.append(point)
    cumulative_m = cumulative_distances(coords)
    return RoadRoute(
        summary=label,
        coords=tuple(coords),
        cumulative_m=tuple(cumulative_m),
        cumulative_s=tuple(d / speed_mps for d in cumulative_m),
    )


class OsrmRouter:
    """OSRM `route` service. The public demo server needs no key but is rate limited."""

    source = "osrm"

    def __init__(self, http: httpx.Client, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    def routes(self, waypoints: Sequence[LonLat], *, alternatives: bool) -> list[RoadRoute]:
        path = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in waypoints)
        params = {
            "alternatives": "3" if alternatives else "false",
            "overview": "full",
            "geometries": "polyline6",
            "annotations": "distance,duration",
            # Only the leg summaries (main roads, e.g. "I 65, I 75") are kept; steps are discarded.
            "steps": "true",
        }
        try:
            response = self._http.get(f"{self._base_url}/route/v1/driving/{path}", params=params)
        except httpx.HTTPError as exc:
            raise upstream_unavailable("routing", type(exc).__name__) from exc
        if response.status_code == 429:
            raise upstream_unavailable("routing", "the provider is rate limiting us")
        try:
            body = response.json()
        except ValueError as exc:
            raise upstream_unavailable("routing", "unreadable response") from exc
        code = body.get("code") if isinstance(body, dict) else None
        # NoRoute: nothing connects the points. NoSegment: a point is nowhere near a road.
        if code in ("NoRoute", "NoSegment"):
            return []
        if response.status_code >= 400 or code != "Ok":
            raise upstream_unavailable("routing", f"provider answered {code or response.status_code}")
        try:
            return [_from_osrm(raw) for raw in body["routes"]]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise upstream_unavailable("routing", "unreadable response") from exc


def _from_osrm(raw: dict[str, Any]) -> RoadRoute:
    coords = decode_polyline(raw["geometry"], precision=6)
    legs = raw["legs"]
    seg_m = [float(d) for leg in legs for d in leg["annotation"]["distance"]]
    seg_s = [float(s) for leg in legs for s in leg["annotation"]["duration"]]
    if len(seg_m) == len(coords) - 1 and len(seg_s) == len(seg_m):
        cumulative_m, cumulative_s = [0.0], [0.0]
        for d, s in zip(seg_m, seg_s, strict=True):
            cumulative_m.append(cumulative_m[-1] + d)
            cumulative_s.append(cumulative_s[-1] + s)
    else:
        # Annotations don't line up with the geometry: spread the totals by distance instead.
        cumulative_m = cumulative_distances(coords)
        total_m = cumulative_m[-1] or 1.0
        scale_m = float(raw["distance"]) / total_m
        rate_s = float(raw["duration"]) / total_m
        cumulative_s = [d * rate_s for d in cumulative_m]
        cumulative_m = [d * scale_m for d in cumulative_m]
    return RoadRoute(
        summary=_summary(leg.get("summary", "") for leg in legs),
        coords=tuple(coords),
        cumulative_m=tuple(cumulative_m),
        cumulative_s=tuple(cumulative_s),
    )


def _summary(parts: Any) -> str:
    """'I 65, I 75' + 'I 75, I 85' -> 'I 65, I 75, I 85'. ';' joins concurrent refs ('I 40; I 75')."""
    seen: dict[str, None] = {}
    for part in parts:
        for road in str(part).replace(";", ",").split(","):
            road = road.strip()
            if road:
                seen.setdefault(road, None)
    return ", ".join(seen)
