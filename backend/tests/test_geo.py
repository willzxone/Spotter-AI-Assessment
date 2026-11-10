from __future__ import annotations

import pytest

from common.geo import (
    bearing_deg,
    cumulative_distances,
    decode_polyline,
    destination,
    haversine_m,
    interpolate,
    locate,
    simplify,
    snap,
)
from tests.conftest import encode_polyline

CHICAGO = (-87.6298, 41.8781)
ATLANTA = (-84.388, 33.749)


def test_haversine_chicago_atlanta() -> None:
    # Great-circle distance is about 944 km (587 mi).
    assert haversine_m(CHICAGO, ATLANTA) == pytest.approx(944_000, rel=0.005)
    assert haversine_m(CHICAGO, CHICAGO) == 0


def test_destination_inverts_bearing_and_distance() -> None:
    there = destination(CHICAGO, bearing_deg(CHICAGO, ATLANTA), haversine_m(CHICAGO, ATLANTA))
    assert haversine_m(there, ATLANTA) < 1.0


def test_decode_polyline_reference_example() -> None:
    # Google's documented example, at precision 5. Output is (lon, lat).
    assert decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5) == [
        (-120.2, 38.5),
        (-120.95, 40.7),
        (-126.453, 43.252),
    ]


def test_decode_polyline_round_trips_precision_6() -> None:
    coords = [(-87.629800, 41.878100), (-86.158100, 39.768400), (-84.388000, 33.749000)]
    assert decode_polyline(encode_polyline(coords), precision=6) == coords


def test_locate_and_interpolate() -> None:
    coords = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
    cumulative = cumulative_distances(coords)
    point = locate(coords, cumulative, cumulative[1] * 1.5)
    assert point.segment == 1
    assert point.fraction == pytest.approx(0.5)
    assert point.coord == pytest.approx((0.0, 1.5))
    assert interpolate([0.0, 10.0, 30.0], point) == pytest.approx(20.0)


def test_locate_clamps_to_the_line() -> None:
    coords = [(0.0, 0.0), (0.0, 1.0)]
    cumulative = cumulative_distances(coords)
    assert locate(coords, cumulative, -5).coord == (0.0, 0.0)
    assert locate(coords, cumulative, cumulative[-1] + 1000).coord == pytest.approx((0.0, 1.0))


def test_simplify_drops_collinear_points_and_keeps_corners() -> None:
    straight = [(0.0, i / 10) for i in range(11)]
    assert simplify(straight, tolerance_m=50) == [0, 10]

    corner = [(0.0, 0.0), (0.0, 0.5), (0.0, 1.0), (0.5, 1.0), (1.0, 1.0)]
    assert simplify(corner, tolerance_m=50) == [0, 2, 4]


def test_snap_returns_the_centre_of_the_grid_cell() -> None:
    assert snap((-87.6298, 41.8781), 0.25) == (-87.625, 41.875)
    assert snap((-84.388, 33.749), 0.25) == (-84.375, 33.625)
    # Every point in a cell shares one forecast.
    assert snap((-87.51, 41.99), 0.25) == snap((-87.74, 41.76), 0.25)
