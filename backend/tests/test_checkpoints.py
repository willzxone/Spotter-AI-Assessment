from __future__ import annotations

import itertools

import pytest

from common.geo import cumulative_distances, destination
from modules.routing.dto import RoadRoute
from modules.trips.checkpoints import place
from modules.trips.constants import METERS_PER_MILE

SPEED_MPS = 25.0  # ~56 mph


def straight_road(miles: float) -> RoadRoute:
    """A road due east from (0, 0), one vertex per mile, driven at a constant speed."""
    steps = int(miles)
    coords = [destination((0.0, 0.0), 90, k * METERS_PER_MILE) for k in range(steps + 1)]
    if miles > steps:
        coords.append(destination((0.0, 0.0), 90, miles * METERS_PER_MILE))
    cumulative_m = cumulative_distances(coords)
    return RoadRoute(
        summary="Test Road",
        coords=tuple(coords),
        cumulative_m=tuple(cumulative_m),
        cumulative_s=tuple(d / SPEED_MPS for d in cumulative_m),
    )


def test_checkpoints_every_interval_plus_both_ends() -> None:
    road = straight_road(110)
    cps = place(road, 25 * METERS_PER_MILE)
    miles = [round(cp.at_m / METERS_PER_MILE, 3) for cp in cps]
    assert miles == [0, 25, 50, 75, 100, 110]
    assert [cp.index for cp in cps] == list(range(6))


def test_eta_follows_the_route_timing() -> None:
    road = straight_road(110)
    cps = place(road, 25 * METERS_PER_MILE)
    assert cps[0].eta_s == 0
    assert cps[-1].eta_s == pytest.approx(road.duration_s)
    for cp in cps:
        assert cp.eta_s == pytest.approx(cp.at_m / SPEED_MPS, rel=1e-6)


def test_coverage_splits_the_road_without_gaps() -> None:
    """Each checkpoint stands for the road halfway to its neighbours; together they cover it once."""
    road = straight_road(110)
    cps = place(road, 25 * METERS_PER_MILE)
    assert cps[0].covers_from_m == 0
    assert cps[-1].covers_to_m == pytest.approx(road.distance_m)
    for a, b in itertools.pairwise(cps):
        assert a.covers_to_m == pytest.approx(b.covers_from_m)
    assert cps[1].covers_from_m == pytest.approx(12.5 * METERS_PER_MILE)


def test_an_end_that_lands_on_a_mark_is_not_duplicated() -> None:
    road = straight_road(100)
    cps = place(road, 25 * METERS_PER_MILE)
    assert len(cps) == 5
    assert cps[-1].at_m == pytest.approx(road.distance_m)


def test_a_route_shorter_than_the_interval_gets_both_ends() -> None:
    road = straight_road(8.5)
    cps = place(road, 25 * METERS_PER_MILE)
    assert [round(cp.at_m / METERS_PER_MILE, 2) for cp in cps] == [0, 8.5]
