"""Weather risk: classify conditions with the brief's table, then apply the load rules."""

from __future__ import annotations

from modules.risk.constants import CONDITIONS, LOAD_RULES, RAIN, SNOW, WIND, ConditionRules, LoadRule
from modules.risk.dto import (
    Assessment,
    BandOut,
    ConditionRulesOut,
    Conditions,
    Factor,
    LevelOut,
    LoadRuleOut,
    RiskLevel,
    RulesOutput,
)


def classify(value: float, rules: ConditionRules) -> RiskLevel:
    level = RiskLevel.LOW
    for threshold in rules.thresholds:
        if value > threshold.value or (threshold.inclusive and value == threshold.value):
            level = threshold.level
    return level


def _load_rule(wind_mph: float, load_lb: int) -> LoadRule | None:
    for rule in LOAD_RULES:
        if rule.wind_min_mph <= wind_mph < rule.wind_max_mph and load_lb > rule.load_over_lb:
            return rule
    return None


def _describe_load_rule(rule: LoadRule) -> str:
    return (
        f"{rule.wind_min_mph:g}–{rule.wind_max_mph - 1:g} mph wind with a load over "
        f"{rule.load_over_lb:,} lb → {rule.level.label}"
    )


def _format(value: float, rules: ConditionRules) -> str:
    amount = f"{value:.0f}" if rules.unit == "mph" else f"{value:.2f}"
    return f"{rules.kind.capitalize()} {amount} {rules.unit}"


def assess(conditions: Conditions, load_lb: int) -> Assessment:
    """The risk at one checkpoint: the worst of wind (after load rules), rain and snow."""
    wind = classify(conditions.wind_mph, WIND)
    rain = classify(conditions.rain_in_hr, RAIN)
    snow = classify(conditions.snow_in_hr, SNOW)

    load_factor: Factor | None = None
    rule = _load_rule(conditions.wind_mph, load_lb)
    if rule is not None and rule.level > wind:
        load_factor = Factor("load", rule.level, _describe_load_rule(rule))

    effective_wind = load_factor.level if load_factor else wind
    level = max(effective_wind, rain, snow)

    drivers: list[Factor] = []
    if level > RiskLevel.LOW:
        if effective_wind == level:
            drivers.append(Factor("wind", wind, _format(conditions.wind_mph, WIND)))
            if load_factor:
                drivers.append(load_factor)
        if rain == level:
            drivers.append(Factor("rain", rain, _format(conditions.rain_in_hr, RAIN)))
        if snow == level:
            drivers.append(Factor("snow", snow, _format(conditions.snow_in_hr, SNOW)))

    return Assessment(
        level=level, wind=wind, rain=rain, snow=snow, load_rule=load_factor, drivers=tuple(drivers)
    )


def _continuous(value: float, rules: ConditionRules) -> float:
    """`level + fraction through the level's band`, so floor(score) == classify(value).

    Used only to shade the heatmap smoothly; every decision uses `classify`.
    """
    level = classify(value, rules)
    if level is RiskLevel.NO_TRAVEL:
        return float(RiskLevel.NO_TRAVEL)
    edges = [0.0, *(t.value for t in rules.thresholds)]
    low, high = edges[level], edges[level + 1]
    fraction = (value - low) / (high - low) if high > low else 0.0
    return level + min(max(fraction, 0.0), 0.999)


def score(conditions: Conditions, load_lb: int) -> float:
    """A 0–4 continuous risk score for the heatmap, consistent with `assess(...).level`."""
    wind = _continuous(conditions.wind_mph, WIND)
    rule = _load_rule(conditions.wind_mph, load_lb)
    if rule is not None:
        wind = max(wind, float(rule.level))
    return max(wind, _continuous(conditions.rain_in_hr, RAIN), _continuous(conditions.snow_in_hr, SNOW))


def rules() -> RulesOutput:
    """The table and load rules, so the UI legend can never drift from the logic."""
    conditions = []
    for condition in CONDITIONS:
        bands = []
        entries = [
            (RiskLevel.LOW, 0.0, True),
            *((t.level, t.value, t.inclusive) for t in condition.thresholds),
        ]
        for i, (level, minimum, min_inclusive) in enumerate(entries):
            nxt = entries[i + 1] if i + 1 < len(entries) else None
            bands.append(
                BandOut(
                    level=level.api_name,
                    min=None if level is RiskLevel.LOW else minimum,
                    max=nxt[1] if nxt is not None else None,
                    min_inclusive=min_inclusive,
                    # The upper edge is included exactly when the next band's entry is not.
                    max_inclusive=nxt is not None and not nxt[2],
                )
            )
        conditions.append(ConditionRulesOut(kind=condition.kind, unit=condition.unit, bands=bands))

    return RulesOutput(
        levels=[LevelOut(level=lvl.api_name, label=lvl.label, score=int(lvl)) for lvl in RiskLevel],
        conditions=conditions,
        load_rules=[
            LoadRuleOut(
                wind_min_mph=rule.wind_min_mph,
                wind_max_mph=rule.wind_max_mph,
                load_over_lb=rule.load_over_lb,
                level=rule.level.api_name,
                text=_describe_load_rule(rule),
            )
            for rule in LOAD_RULES
        ],
    )
