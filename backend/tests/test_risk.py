"""The risk table and load rules from the brief, boundary by boundary."""

from __future__ import annotations

import itertools
import math

import pytest

from modules.risk import service
from modules.risk.constants import RAIN, SNOW, WIND
from modules.risk.dto import Conditions, RiskLevel

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = RiskLevel


@pytest.mark.parametrize(
    ("mph", "level"),
    [
        (0, LOW),
        (24.9, LOW),
        (25, MODERATE),
        (34.9, MODERATE),
        (35, HIGH),
        (44.9, HIGH),
        (45, SEVERE),
        (54.9, SEVERE),
        (55, NO_TRAVEL),  # "≥55 mph"
        (90, NO_TRAVEL),
    ],
)
def test_wind_bands(mph: float, level: RiskLevel) -> None:
    assert service.classify(mph, WIND) is level


@pytest.mark.parametrize(
    ("in_hr", "level"),
    [
        (0, LOW),
        (0.09, LOW),
        (0.10, MODERATE),
        (0.24, MODERATE),
        (0.25, HIGH),  # a shared boundary belongs to the higher band
        (0.49, HIGH),
        (0.50, SEVERE),
        (1.00, SEVERE),  # No Travel is "> 1.00"
        (1.01, NO_TRAVEL),
    ],
)
def test_rain_bands(in_hr: float, level: RiskLevel) -> None:
    assert service.classify(in_hr, RAIN) is level


@pytest.mark.parametrize(
    ("in_hr", "level"),
    [
        (0, LOW),
        (0.49, LOW),
        (0.5, MODERATE),
        (0.99, MODERATE),
        (1.0, HIGH),
        (1.99, HIGH),
        (2.0, SEVERE),
        (3.0, SEVERE),  # No Travel is "> 3.0"
        (3.01, NO_TRAVEL),
    ],
)
def test_snow_bands(in_hr: float, level: RiskLevel) -> None:
    assert service.classify(in_hr, SNOW) is level


@pytest.mark.parametrize(
    ("mph", "load_lb", "level"),
    [
        # 45–54 mph + > 30,000 lb -> No Travel
        (45, 30_001, NO_TRAVEL),
        (54.9, 45_000, NO_TRAVEL),
        (50, 30_000, SEVERE),  # "over" is strict
        (50, 0, SEVERE),
        # 35–44 mph + > 40,000 lb -> Severe
        (35, 40_001, SEVERE),
        (44.9, 80_000, SEVERE),
        (40, 40_000, HIGH),
        (40, 35_000, HIGH),  # over 30k is only a rule in the 45–54 band
        # ≥55 mph is No Travel for any load
        (55, 0, NO_TRAVEL),
        # No load rule below 35 mph
        (30, 80_000, MODERATE),
        (10, 80_000, LOW),
    ],
)
def test_load_rules(mph: float, load_lb: int, level: RiskLevel) -> None:
    assert service.assess(Conditions(mph, 0, 0), load_lb).level is level


def test_load_rule_is_reported_as_a_driver() -> None:
    a = service.assess(Conditions(wind_mph=48, rain_in_hr=0, snow_in_hr=0), load_lb=35_000)
    assert a.wind is SEVERE  # the table alone
    assert a.level is NO_TRAVEL  # after the load rule
    assert a.load_rule is not None
    assert a.load_rule.kind == "load"
    assert a.load_rule.level is NO_TRAVEL
    assert "30,000 lb" in a.load_rule.detail
    assert [d.kind for d in a.drivers] == ["wind", "load"]


def test_load_rule_never_lowers_the_wind_level() -> None:
    a = service.assess(Conditions(wind_mph=60, rain_in_hr=0, snow_in_hr=0), load_lb=35_000)
    assert a.level is NO_TRAVEL
    assert a.load_rule is None


def test_checkpoint_takes_the_worst_condition() -> None:
    a = service.assess(Conditions(wind_mph=10, rain_in_hr=0.3, snow_in_hr=0.6), load_lb=0)
    assert (a.wind, a.rain, a.snow) == (LOW, HIGH, MODERATE)
    assert a.level is HIGH
    assert [(d.kind, d.detail) for d in a.drivers] == [("rain", "Rain 0.30 in/hr")]


def test_every_condition_at_the_worst_level_is_a_driver() -> None:
    a = service.assess(Conditions(wind_mph=36, rain_in_hr=0.3, snow_in_hr=1.5), load_lb=0)
    assert a.level is HIGH
    assert [d.kind for d in a.drivers] == ["wind", "rain", "snow"]


def test_low_risk_has_no_drivers() -> None:
    a = service.assess(Conditions(wind_mph=5, rain_in_hr=0, snow_in_hr=0), load_lb=80_000)
    assert a.level is LOW
    assert a.drivers == ()


def test_heatmap_score_agrees_with_the_level() -> None:
    """floor(score) must be the level `assess` gives, or the heatmap would contradict the routes."""
    winds = [0, 10, 24.9, 25, 30, 34.9, 35, 40, 44.9, 45, 50, 54.9, 55, 70]
    rains = [0, 0.05, 0.1, 0.2, 0.25, 0.4, 0.5, 0.8, 1.0, 1.01, 2]
    snows = [0, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 2.9, 3.0, 3.01]
    loads = [0, 30_000, 35_000, 45_000]
    for wind, rain, snow, load in itertools.product(winds, rains, snows, loads):
        conditions = Conditions(wind, rain, snow)
        score = service.score(conditions, load)
        assert 0 <= score <= 4
        assert math.floor(score) == service.assess(conditions, load).level, (wind, rain, snow, load)


def test_rules_describe_the_table() -> None:
    rules = service.rules()
    assert [lvl.level for lvl in rules.levels] == ["low", "moderate", "high", "severe", "no_travel"]
    assert [lvl.score for lvl in rules.levels] == [0, 1, 2, 3, 4]

    wind, rain, snow = rules.conditions
    assert (wind.kind, wind.unit) == ("wind", "mph")
    assert [(b.min, b.max) for b in wind.bands] == [(None, 25), (25, 35), (35, 45), (45, 55), (55, None)]
    assert wind.bands[-1].min_inclusive is True

    # Rain: exactly 1.00 is Severe, so Severe's upper edge is inclusive and No Travel's lower isn't.
    severe, no_travel = rain.bands[-2:]
    assert (severe.max, severe.max_inclusive) == (1.0, True)
    assert (no_travel.min, no_travel.min_inclusive) == (1.0, False)
    assert snow.bands[-1].min == 3.0

    assert [(r.wind_min_mph, r.load_over_lb, r.level) for r in rules.load_rules] == [
        (45, 30_000, "no_travel"),
        (35, 40_000, "severe"),
    ]
    assert rules.load_rules[0].text == "45–54 mph wind with a load over 30,000 lb → No Travel"
