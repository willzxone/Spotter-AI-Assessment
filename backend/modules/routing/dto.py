"""Shapes other modules receive from routing. Routing has no API surface of its own."""

from __future__ import annotations

from dataclasses import dataclass

from common.geo import LonLat


@dataclass(frozen=True, slots=True)
class RoadRoute:
    """One drivable route at full resolution.

    `cumulative_m[i]` and `cumulative_s[i]` are the driving distance and time from the start
    to `coords[i]`, so an ETA anywhere on the route is a lookup, not a re-estimate.
    """

    summary: str
    coords: tuple[LonLat, ...]
    cumulative_m: tuple[float, ...]
    cumulative_s: tuple[float, ...]

    @property
    def distance_m(self) -> float:
        return self.cumulative_m[-1]

    @property
    def duration_s(self) -> float:
        return self.cumulative_s[-1]
