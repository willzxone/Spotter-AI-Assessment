"""Shapes the risk module hands out — to the API and to other modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Literal

from core.schema import ApiSchema

# `type` aliases (not plain assignments) so the OpenAPI schema names them, and the
# frontend's generated types get `RiskLevelName` rather than the union pasted inline.
type RiskLevelName = Literal["low", "moderate", "high", "severe", "no_travel"]
type ConditionKind = Literal["wind", "rain", "snow"]
type FactorKind = ConditionKind | Literal["load"]


class RiskLevel(IntEnum):
    """Ordered so that `max()` picks the worse level and the value doubles as a 0–4 score."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def api_name(self) -> RiskLevelName:
        return _API_NAMES[self]

    @property
    def label(self) -> str:
        return _LABELS[self]


_API_NAMES: dict[RiskLevel, RiskLevelName] = {
    RiskLevel.LOW: "low",
    RiskLevel.MODERATE: "moderate",
    RiskLevel.HIGH: "high",
    RiskLevel.SEVERE: "severe",
    RiskLevel.NO_TRAVEL: "no_travel",
}
_LABELS = {
    RiskLevel.LOW: "Low",
    RiskLevel.MODERATE: "Moderate",
    RiskLevel.HIGH: "High",
    RiskLevel.SEVERE: "Severe",
    RiskLevel.NO_TRAVEL: "No Travel",
}


@dataclass(frozen=True, slots=True)
class Conditions:
    """Weather at one place and time, in the units the risk table uses."""

    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class Factor:
    kind: FactorKind
    level: RiskLevel
    detail: str


@dataclass(frozen=True, slots=True)
class Assessment:
    level: RiskLevel
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    # The load rule that raised the wind level for this truck, if any.
    load_rule: Factor | None
    # What put the checkpoint at `level` (empty when the level is Low).
    drivers: tuple[Factor, ...]


# ---- API shapes for `risk.rules` -------------------------------------------------


class BandOut(ApiSchema):
    level: RiskLevelName
    min: float | None
    max: float | None
    min_inclusive: bool
    max_inclusive: bool


class ConditionRulesOut(ApiSchema):
    kind: ConditionKind
    unit: str
    bands: list[BandOut]


class LoadRuleOut(ApiSchema):
    wind_min_mph: float
    wind_max_mph: float | None
    load_over_lb: int
    level: RiskLevelName
    text: str


class LevelOut(ApiSchema):
    level: RiskLevelName
    label: str
    score: int


class RulesOutput(ApiSchema):
    levels: list[LevelOut]
    conditions: list[ConditionRulesOut]
    load_rules: list[LoadRuleOut]
