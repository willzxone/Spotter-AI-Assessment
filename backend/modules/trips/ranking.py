"""Route recommendation.

Routes are compared on these criteria, in order; the first one that differs decides:

0. Fewest No Travel miles. The brief ranks Severe first, but No Travel is stricter than
   Severe, so a route that crosses it can never beat one that doesn't.
1. Fewest Severe miles.
2. Fewest High miles.
3. Lowest average risk: the mile-weighted mean of checkpoint levels (Low 0 ... No Travel 4).
4. Shortest travel time.

Miles are compared to 0.1 mi, average risk to 0.01 and time to the minute, so noise in the
last decimal never overrules a later criterion.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from modules.risk.dto import RiskLevel


@dataclass(frozen=True, slots=True)
class RouteRisk:
    id: str
    miles: dict[RiskLevel, float]
    average: float
    worst: RiskLevel
    duration_s: float


@dataclass(frozen=True, slots=True)
class _Criterion:
    key: Callable[[RouteRisk], float]
    describe: Callable[[RouteRisk], str]
    better: str  # "fewer Severe miles"
    worse: str


def _miles(level: RiskLevel) -> _Criterion:
    name = level.label
    return _Criterion(
        key=lambda r: round(r.miles[level], 1),
        describe=lambda r: f"{r.miles[level]:.0f} mi",
        better=f"fewest {name} miles",
        worse=f"more {name} miles",
    )


def format_duration(seconds: float) -> str:
    minutes = round(seconds / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"


CRITERIA: tuple[_Criterion, ...] = (
    _miles(RiskLevel.NO_TRAVEL),
    _miles(RiskLevel.SEVERE),
    _miles(RiskLevel.HIGH),
    _Criterion(
        key=lambda r: round(r.average, 2),
        describe=lambda r: f"{r.average:.2f}",
        better="lowest average risk",
        worse="higher average risk",
    ),
    _Criterion(
        key=lambda r: round(r.duration_s / 60),
        describe=lambda r: format_duration(r.duration_s),
        better="shortest travel time",
        worse="longer travel time",
    ),
)


def summarize(id_: str, spans: Sequence[tuple[RiskLevel, float]], duration_s: float) -> RouteRisk:
    """`spans` is (level, miles) for each checkpoint's stretch of road."""
    miles = dict.fromkeys(RiskLevel, 0.0)
    for level, length in spans:
        miles[level] += length
    total = sum(miles.values())
    average = sum(level * length for level, length in miles.items()) / total if total else 0.0
    worst = max((level for level, length in spans if length > 0), default=RiskLevel.LOW)
    return RouteRisk(id=id_, miles=miles, average=average, worst=worst, duration_s=duration_s)


def sort_key(route: RouteRisk) -> tuple[float, ...]:
    return tuple(c.key(route) for c in CRITERIA)


def rank(routes: Sequence[RouteRisk]) -> list[RouteRisk]:
    """Best first. `sorted` is stable, so a full tie keeps the faster-first input order."""
    return sorted(routes, key=sort_key)


def _decider(a: RouteRisk, b: RouteRisk) -> _Criterion | None:
    for criterion in CRITERIA:
        if criterion.key(a) != criterion.key(b):
            return criterion
    return None


def verdicts(ranked: Sequence[RouteRisk]) -> dict[str, str]:
    """One sentence per route: why the best one wins, and what puts each other one behind it."""
    best = ranked[0]
    out: dict[str, str] = {}
    if len(ranked) == 1:
        out[best.id] = "Recommended: the only route between these places."
        return out
    runner_up = ranked[1]
    decider = _decider(best, runner_up)
    if decider is None:
        out[best.id] = f"Recommended: ties with Route {runner_up.id} on every criterion."
    else:
        out[best.id] = (
            f"Recommended: {decider.better} "
            f"({decider.describe(best)} vs {decider.describe(runner_up)} on Route {runner_up.id})."
        )
    for other in ranked[1:]:
        decider = _decider(other, best)
        if decider is None:
            out[other.id] = f"Ties with Route {best.id} on every criterion."
        else:
            # Not str.capitalize(): it would lowercase the level name ("more Severe" -> "More severe").
            worse = decider.worse[:1].upper() + decider.worse[1:]
            out[other.id] = (
                f"{worse} than Route {best.id} ({decider.describe(other)} vs {decider.describe(best)})."
            )
    return out
