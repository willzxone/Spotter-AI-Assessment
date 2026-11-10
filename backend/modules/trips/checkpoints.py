"""Where along a route the weather is sampled, and when the truck gets there."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from common.geo import LonLat, interpolate, locate
from modules.routing.dto import RoadRoute


@dataclass(frozen=True, slots=True)
class Checkpoint:
    index: int
    at_m: float
    coord: LonLat
    # Driving time from departure, from the routing provider's per-segment durations.
    eta_s: float
    # The stretch of road this checkpoint stands for: halfway to each neighbour, so the
    # stretches tile the route exactly and every mile is counted once.
    covers_from_m: float
    covers_to_m: float


def place(route: RoadRoute, interval_m: float) -> list[Checkpoint]:
    """A checkpoint at the origin, every `interval_m` after it, and at the destination."""
    total = route.distance_m
    marks = [k * interval_m for k in range(int(total // interval_m) + 1)]
    if total - marks[-1] > 1.0:
        marks.append(total)
    else:
        marks[-1] = total

    edges = [0.0, *((a + b) / 2 for a, b in itertools.pairwise(marks)), total]
    checkpoints: list[Checkpoint] = []
    for i, at in enumerate(marks):
        point = locate(route.coords, route.cumulative_m, at)
        checkpoints.append(
            Checkpoint(
                index=i,
                at_m=at,
                coord=point.coord,
                eta_s=interpolate(route.cumulative_s, point),
                covers_from_m=edges[i],
                covers_to_m=edges[i + 1],
            )
        )
    return checkpoints
