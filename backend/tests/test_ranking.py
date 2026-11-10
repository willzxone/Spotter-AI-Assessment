"""Recommendation order: No Travel, Severe, High miles, then average risk, then time."""

from __future__ import annotations

from modules.risk.dto import RiskLevel
from modules.trips.ranking import RouteRisk, format_duration, rank, summarize, verdicts

LOW, MODERATE, HIGH, SEVERE, NO_TRAVEL = RiskLevel
HOUR = 3600.0


def route(
    id_: str,
    *,
    hours: float = 10,
    severe: float = 0,
    high: float = 0,
    moderate: float = 0,
    no_travel: float = 0,
    total: float = 600,
) -> RouteRisk:
    low = total - severe - high - moderate - no_travel
    spans = [(LOW, low), (MODERATE, moderate), (HIGH, high), (SEVERE, severe), (NO_TRAVEL, no_travel)]
    return summarize(id_, spans, hours * HOUR)


def ids(routes: list[RouteRisk]) -> list[str]:
    return [r.id for r in routes]


def test_summarize() -> None:
    r = summarize("A", [(LOW, 10), (SEVERE, 5), (LOW, 5)], 2 * HOUR)
    assert r.miles[SEVERE] == 5
    assert r.miles[LOW] == 15
    assert r.average == 0.75  # (3 * 5) / 20
    assert r.worst is SEVERE


def test_fewest_severe_miles_beats_a_faster_route() -> None:
    fast = route("A", hours=9, severe=40)
    slow = route("B", hours=12, severe=5, high=200)
    assert ids(rank([fast, slow])) == ["B", "A"]


def test_no_travel_miles_rank_before_severe() -> None:
    blocked = route("A", no_travel=1)
    stormy = route("B", severe=50)
    assert ids(rank([blocked, stormy])) == ["B", "A"]


def test_then_high_miles() -> None:
    a = route("A", hours=9, severe=5, high=80)
    b = route("B", hours=11, severe=5, high=20)
    assert ids(rank([a, b])) == ["B", "A"]


def test_then_average_risk() -> None:
    a = route("A", hours=9, moderate=300)
    b = route("B", hours=11, moderate=10)
    assert ids(rank([a, b])) == ["B", "A"]


def test_then_travel_time() -> None:
    a = route("A", hours=11)
    b = route("B", hours=9)
    assert ids(rank([a, b])) == ["B", "A"]


def test_rounding_noise_never_overrules_a_later_criterion() -> None:
    # 0.01 Severe miles apart is noise; the 2-hour time difference decides.
    a = route("A", hours=12, severe=10.01)
    b = route("B", hours=10, severe=10.02)
    assert ids(rank([a, b])) == ["B", "A"]


def test_full_tie_keeps_the_faster_first_input_order() -> None:
    assert ids(rank([route("A"), route("B"), route("C")])) == ["A", "B", "C"]


def test_verdicts_name_the_deciding_criterion() -> None:
    ranked = rank([route("A", hours=9, severe=40), route("B", hours=12, severe=5), route("C", hours=13)])
    out = verdicts(ranked)
    assert out["C"] == "Recommended: fewest Severe miles (0 mi vs 5 mi on Route B)."
    assert out["B"] == "More Severe miles than Route C (5 mi vs 0 mi)."
    assert out["A"] == "More Severe miles than Route C (40 mi vs 0 mi)."


def test_verdict_keeps_multi_word_level_names_capitalised() -> None:
    out = verdicts(rank([route("A", no_travel=3), route("B")]))
    assert out["A"] == "More No Travel miles than Route B (3 mi vs 0 mi)."


def test_verdict_for_a_single_route_and_a_tie() -> None:
    assert verdicts([route("A")]) == {"A": "Recommended: the only route between these places."}
    tied = verdicts([route("A"), route("B")])
    assert tied["A"] == "Recommended: ties with Route B on every criterion."
    assert tied["B"] == "Ties with Route A on every criterion."


def test_format_duration() -> None:
    assert format_duration(600) == "10 min"
    assert format_duration(3720) == "1 h 02 min"
    assert format_duration(13 * HOUR + 59.6 * 60) == "14 h 00 min"
