"""The risk table and load rules from the assessment brief — the single source of truth.

Bands are written as the *entry point* of each level above Low. A value that
lands exactly on a shared boundary belongs to the higher band (`25 mph` is
Moderate, `0.25 in/hr` is High), except where the brief says "greater than"
for No Travel: rain of exactly `1.00 in/hr` and snow of exactly `3.0 in/hr`
are still Severe.

    Condition | Low      | Moderate  | High      | Severe    | No Travel
    Wind      | <25 mph  | 25–34     | 35–44     | 45–54     | ≥55 mph
    Rain      | <0.10    | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | >1.00 in/hr
    Snow      | <0.5     | 0.5–1.0   | 1.0–2.0   | 2.0–3.0   | >3.0 in/hr
"""

from __future__ import annotations

from dataclasses import dataclass

from modules.risk.dto import ConditionKind, RiskLevel


@dataclass(frozen=True, slots=True)
class Threshold:
    level: RiskLevel
    value: float
    # True: reaching `value` enters the level. False: it must be exceeded.
    inclusive: bool


@dataclass(frozen=True, slots=True)
class ConditionRules:
    kind: ConditionKind
    unit: str
    thresholds: tuple[Threshold, ...]  # ascending, one per level above Low


WIND = ConditionRules(
    kind="wind",
    unit="mph",
    thresholds=(
        Threshold(RiskLevel.MODERATE, 25, inclusive=True),
        Threshold(RiskLevel.HIGH, 35, inclusive=True),
        Threshold(RiskLevel.SEVERE, 45, inclusive=True),
        Threshold(RiskLevel.NO_TRAVEL, 55, inclusive=True),
    ),
)

RAIN = ConditionRules(
    kind="rain",
    unit="in/hr",
    thresholds=(
        Threshold(RiskLevel.MODERATE, 0.10, inclusive=True),
        Threshold(RiskLevel.HIGH, 0.25, inclusive=True),
        Threshold(RiskLevel.SEVERE, 0.50, inclusive=True),
        Threshold(RiskLevel.NO_TRAVEL, 1.00, inclusive=False),
    ),
)

SNOW = ConditionRules(
    kind="snow",
    unit="in/hr",
    thresholds=(
        Threshold(RiskLevel.MODERATE, 0.5, inclusive=True),
        Threshold(RiskLevel.HIGH, 1.0, inclusive=True),
        Threshold(RiskLevel.SEVERE, 2.0, inclusive=True),
        Threshold(RiskLevel.NO_TRAVEL, 3.0, inclusive=False),
    ),
)

CONDITIONS = (WIND, RAIN, SNOW)


@dataclass(frozen=True, slots=True)
class LoadRule:
    """Wind in [wind_min_mph, wind_max_mph) with a load over `load_over_lb` → `level`."""

    wind_min_mph: float
    wind_max_mph: float
    load_over_lb: int
    level: RiskLevel


# ≥55 mph is No Travel for any load — the wind table already says so.
LOAD_RULES = (
    LoadRule(wind_min_mph=45, wind_max_mph=55, load_over_lb=30_000, level=RiskLevel.NO_TRAVEL),
    LoadRule(wind_min_mph=35, wind_max_mph=45, load_over_lb=40_000, level=RiskLevel.SEVERE),
)
