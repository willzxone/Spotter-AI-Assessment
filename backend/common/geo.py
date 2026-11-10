"""Framework-free geometry helpers shared by modules.

Coordinates are `(lon, lat)` tuples in degrees everywhere in this file — the
GeoJSON order — so they can be handed to the map without reshuffling.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344

LonLat = tuple[float, float]


def haversine_m(a: LonLat, b: LonLat) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a: LonLat, b: LonLat) -> float:
    """Initial great-circle bearing from `a` to `b`, clockwise from north."""
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def destination(origin: LonLat, bearing: float, distance_m: float) -> LonLat:
    """The point `distance_m` away from `origin` along `bearing` (great circle)."""
    lon1, lat1 = math.radians(origin[0]), math.radians(origin[1])
    theta, delta = math.radians(bearing), distance_m / EARTH_RADIUS_M
    lat2 = math.asin(math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(theta))
    lon2 = lon1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(lat1),
        math.cos(delta) - math.sin(lat1) * math.sin(lat2),
    )
    return ((math.degrees(lon2) + 540) % 360 - 180, math.degrees(lat2))


def cumulative_distances(coords: Sequence[LonLat]) -> list[float]:
    total = 0.0
    out = [0.0]
    for i in range(1, len(coords)):
        total += haversine_m(coords[i - 1], coords[i])
        out.append(total)
    return out


@dataclass(frozen=True, slots=True)
class PointOnLine:
    coord: LonLat
    segment: int  # index of the vertex that starts the segment holding the point
    fraction: float  # 0..1 position inside that segment


def locate(coords: Sequence[LonLat], cumulative_m: Sequence[float], distance_m: float) -> PointOnLine:
    """The point `distance_m` along a polyline, clamped to its ends."""
    if distance_m <= 0 or len(coords) == 1:
        return PointOnLine(coords[0], 0, 0.0)
    if distance_m >= cumulative_m[-1]:
        return PointOnLine(coords[-1], len(coords) - 2, 1.0)
    i = bisect_right(cumulative_m, distance_m) - 1
    span = cumulative_m[i + 1] - cumulative_m[i]
    f = 0.0 if span <= 0 else (distance_m - cumulative_m[i]) / span
    a, b = coords[i], coords[i + 1]
    return PointOnLine((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), i, f)


def interpolate(values: Sequence[float], at: PointOnLine) -> float:
    """Linear interpolation of a per-vertex series at a located point."""
    i = at.segment
    if i + 1 >= len(values):
        return values[-1]
    return values[i] + (values[i + 1] - values[i]) * at.fraction


def decode_polyline(encoded: str, precision: int = 6) -> list[LonLat]:
    """Decode a Google encoded polyline (OSRM `polyline6` by default) into (lon, lat)."""
    factor = 10**precision
    coords: list[LonLat] = []
    index = lat = lon = 0
    length = len(encoded)
    while index < length:
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        coords.append((lon / factor, lat / factor))
    return coords


def simplify(coords: Sequence[LonLat], tolerance_m: float) -> list[int]:
    """Radial-distance prefilter followed by Ramer–Douglas–Peucker.

    Returns the indices (into `coords`) of the vertices to keep. Distances are
    measured on a local equirectangular projection, which is exact enough at
    route scale. The prefilter drops vertices closer than `tolerance_m` to the
    last kept one — they can never matter at that tolerance — so RDP only walks
    the vertices that shape the line.
    """
    n = len(coords)
    if n <= 2:
        return list(range(n))
    sample = coords[:: max(1, n // 64)]
    mid_lat = math.radians(sum(c[1] for c in sample) / len(sample))
    kx = math.cos(mid_lat) * math.pi / 180 * EARTH_RADIUS_M
    ky = math.pi / 180 * EARTH_RADIUS_M
    tol2 = tolerance_m * tolerance_m

    index = [0]
    lx, ly = coords[0][0] * kx, coords[0][1] * ky
    for i in range(1, n - 1):
        x, y = coords[i][0] * kx, coords[i][1] * ky
        if (x - lx) ** 2 + (y - ly) ** 2 >= tol2:
            index.append(i)
            lx, ly = x, y
    index.append(n - 1)

    xs = [coords[i][0] * kx for i in index]
    ys = [coords[i][1] * ky for i in index]
    m = len(index)
    keep = [False] * m
    keep[0] = keep[-1] = True
    stack = [(0, m - 1)]
    while stack:
        start, end = stack.pop()
        ax, ay, bx, by = xs[start], ys[start], xs[end], ys[end]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        worst, worst_d2 = -1, tol2
        for i in range(start + 1, end):
            px, py = xs[i] - ax, ys[i] - ay
            if seg2 == 0:
                d2 = px * px + py * py
            else:
                t = max(0.0, min(1.0, (px * dx + py * dy) / seg2))
                ex, ey = px - t * dx, py - t * dy
                d2 = ex * ex + ey * ey
            if d2 > worst_d2:
                worst, worst_d2 = i, d2
        if worst != -1:
            keep[worst] = True
            stack.append((start, worst))
            stack.append((worst, end))
    return [index[i] for i, k in enumerate(keep) if k]


def snap(coord: LonLat, step_deg: float) -> LonLat:
    """Snap to the centre of a `step_deg` grid cell (used to share forecasts between nearby points)."""
    return (
        round((math.floor(coord[0] / step_deg) + 0.5) * step_deg, 4),
        round((math.floor(coord[1] / step_deg) + 0.5) * step_deg, 4),
    )
