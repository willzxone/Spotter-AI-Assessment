"""End to end through the real URL conf, middleware and kernel, on the simulated adapters."""

from __future__ import annotations

import dataclasses
import itertools
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from django.test import Client

from core import views
from core.config import get_config
from tests.conftest import Rpc, plan_body, soon

LEVELS = ["low", "moderate", "high", "severe", "no_travel"]


def assert_error(response, status: int, code: str) -> dict:  # type: ignore[no-untyped-def,type-arg]
    assert response.status_code == status, response.content
    error = response.json()["error"]
    assert error["code"] == code
    assert error["requestId"] == response["X-Request-Id"]
    return error  # type: ignore[no-any-return]


# ---- trips/plan ------------------------------------------------------------------------------


def test_plan_returns_three_ranked_routes(rpc: Rpc) -> None:
    response = rpc("trips/plan", plan_body())
    assert response.status_code == 200, response.content
    plan = response.json()

    assert plan["loadLb"] == 35_000
    assert plan["intervalMi"] == 25
    assert plan["sources"] == {"routing": "simulated", "weather": "simulated"}

    routes = plan["routes"]
    assert [r["id"] for r in routes] == ["A", "B", "C"]
    durations = [r["durationS"] for r in routes]
    assert durations == sorted(durations)  # listed fastest first
    assert sorted(r["rank"] for r in routes) == [1, 2, 3]
    (best,) = [r for r in routes if r["recommended"]]
    assert best["rank"] == 1
    assert best["id"] == plan["recommendedId"]
    assert best["verdict"].startswith("Recommended")


def test_plan_route_details(rpc: Rpc) -> None:
    plan = rpc("trips/plan", plan_body(intervalMi=50)).json()
    departure = datetime.fromisoformat(plan["departureAt"])
    for route in plan["routes"]:
        cps = route["checkpoints"]
        assert cps[0]["mile"] == 0
        assert cps[-1]["mile"] == pytest.approx(route["distanceMi"], abs=0.1)
        assert all(b["mile"] - a["mile"] <= 50.01 for a, b in itertools.pairwise(cps))
        assert [cp["index"] for cp in cps] == list(range(len(cps)))

        etas = [datetime.fromisoformat(cp["eta"]) for cp in cps]
        assert etas[0] == departure
        assert etas == sorted(etas)
        assert abs(datetime.fromisoformat(route["arrivalAt"]) - etas[-1]) <= timedelta(minutes=1)

        for cp in cps:
            assert cp["level"] in LEVELS
            assert LEVELS.index(cp["level"]) >= max(
                LEVELS.index(cp["windLevel"]), LEVELS.index(cp["rainLevel"]), LEVELS.index(cp["snowLevel"])
            )
            assert (cp["drivers"] == []) == (cp["level"] == "low")

        # Every mile is counted once, at the level of the checkpoint that covers it.
        miles = route["risk"]["miles"]
        assert sum(miles.values()) == pytest.approx(route["distanceMi"], abs=0.1)
        assert route["risk"]["worst"] == max((cp["level"] for cp in cps), key=LEVELS.index)

        # The coloured segments run end to end along the route.
        segments = route["segments"]
        assert segments[0]["fromMi"] == 0
        assert segments[-1]["toMi"] == pytest.approx(route["distanceMi"], abs=0.1)
        for a, b in itertools.pairwise(segments):
            assert a["toMi"] == b["fromMi"]
            assert a["level"] != b["level"]


@pytest.mark.parametrize("interval", [10, 25, 50])
def test_every_brief_interval_is_accepted(rpc: Rpc, interval: int) -> None:
    plan = rpc("trips/plan", plan_body(intervalMi=interval)).json()
    route = plan["routes"][0]
    expected = int(route["distanceMi"] // interval) + 1
    assert len(route["checkpoints"]) in (expected, expected + 1)


def test_heatmap_covers_the_trip_for_at_least_48_hours(rpc: Rpc) -> None:
    plan = rpc("trips/plan", plan_body()).json()
    heatmap = plan["heatmap"]
    assert heatmap["hours"] >= 48
    assert heatmap["cells"]
    for cell in heatmap["cells"]:
        assert len(cell["scores"]) == heatmap["hours"] + 1
        assert all(0 <= s <= 4 for s in cell["scores"])
    assert datetime.fromisoformat(heatmap["start"]) <= datetime.fromisoformat(plan["departureAt"])


def test_heavier_loads_are_never_safer(rpc: Rpc) -> None:
    light = rpc("trips/plan", plan_body(loadLb=10_000)).json()
    heavy = rpc("trips/plan", plan_body(loadLb=80_000)).json()
    for lr, hr in zip(light["routes"], heavy["routes"], strict=True):
        for lc, hc in zip(lr["checkpoints"], hr["checkpoints"], strict=True):
            assert LEVELS.index(hc["level"]) >= LEVELS.index(lc["level"])


@pytest.mark.parametrize(
    ("overrides", "path"),
    [
        ({"intervalMi": 30}, "intervalMi"),
        ({"loadLb": -1}, "loadLb"),
        ({"loadLb": 500_000}, "loadLb"),
        ({"origin": {"lat": 95, "lon": 0, "label": "x"}}, "origin.lat"),
        ({"departureAt": "tomorrow"}, "departureAt"),
        ({"departureAt": "2026-11-10T14:00:00"}, "departureAt"),  # no timezone
        ({"surprise": True}, "surprise"),
    ],
)
def test_plan_validation(rpc: Rpc, overrides: dict, path: str) -> None:  # type: ignore[type-arg]
    error = assert_error(rpc("trips/plan", plan_body(**overrides)), 422, "VALIDATION_FAILED")
    assert path in [issue["path"] for issue in error["data"]["issues"]]


def test_plan_needs_every_field_but_the_interval(rpc: Rpc) -> None:
    error = assert_error(rpc("trips/plan", {}), 422, "VALIDATION_FAILED")
    paths = {issue["path"] for issue in error["data"]["issues"]}
    assert paths == {"origin", "destination", "departureAt", "loadLb"}

    body = plan_body()
    del body["intervalMi"]
    assert rpc("trips/plan", body).json()["intervalMi"] == 25


@pytest.mark.parametrize(
    ("departure", "message"),
    [(soon(-2), "past"), (soon(24 * 30), "within")],
)
def test_departure_window(rpc: Rpc, departure: str, message: str) -> None:
    error = assert_error(rpc("trips/plan", plan_body(departureAt=departure)), 400, "BAD_REQUEST")
    assert message in error["message"]
    assert error["data"] == {"field": "departureAt"}


def test_same_origin_and_destination(rpc: Rpc) -> None:
    body = plan_body(destination=plan_body()["origin"])
    error = assert_error(rpc("trips/plan", body), 400, "BAD_REQUEST")
    assert "same place" in error["message"]


def test_malformed_json_is_a_validation_error(client: Client) -> None:
    response = client.post("/rpc/trips/plan", data="{nope", content_type="application/json")
    assert response.status_code in (400, 422)
    assert response.json()["error"]["code"] in ("BAD_REQUEST", "VALIDATION_FAILED")


# ---- other procedures ------------------------------------------------------------------------


def test_geocoding_search(rpc: Rpc) -> None:
    response = rpc("geocoding/search", {"query": "dal", "limit": 5})
    assert response.status_code == 200
    (place,) = response.json()["places"]
    assert place["label"] == "Dallas, Texas, United States"
    assert {"id", "name", "lat", "lon", "kind"} <= place.keys()


def test_geocoding_query_is_validated(rpc: Rpc) -> None:
    assert_error(rpc("geocoding/search", {"query": " ", "limit": 5}), 422, "VALIDATION_FAILED")
    assert_error(rpc("geocoding/search", {"query": "dal", "limit": 50}), 422, "VALIDATION_FAILED")


def test_risk_rules(rpc: Rpc) -> None:
    rules = rpc("risk/rules").json()
    assert [c["kind"] for c in rules["conditions"]] == ["wind", "rain", "snow"]
    assert len(rules["loadRules"]) == 2


def test_procedures_are_throttled_per_client(rpc: Rpc) -> None:
    for _ in range(90):
        assert rpc("geocoding/search", {"query": "dal", "limit": 5}).status_code == 200
    error = assert_error(rpc("geocoding/search", {"query": "dal", "limit": 5}), 429, "RATE_LIMITED")
    assert error["data"]["retryAfterS"] > 0


def test_unknown_procedure(rpc: Rpc) -> None:
    error = assert_error(rpc("trips/nope"), 404, "NOT_FOUND")
    assert "/rpc/trips/nope" in error["message"]


# ---- cross-cutting ---------------------------------------------------------------------------


def test_request_id_is_echoed_when_valid_and_minted_otherwise(rpc: Rpc) -> None:
    assert rpc("risk/rules", **{"X-Request-Id": "trace-1234abcd"})["X-Request-Id"] == "trace-1234abcd"
    minted = rpc("risk/rules", **{"X-Request-Id": "bad id with spaces"})["X-Request-Id"]
    assert len(minted) == 32
    assert rpc("risk/rules")["X-Request-Id"] != minted


def test_health_probes(client: Client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_spa_shell(client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Both cases use their own dist dir, so the result never depends on whether
    # the real frontend/ has been built on this machine.
    dist = tmp_path / "dist"
    dist.mkdir()
    config = dataclasses.replace(get_config(), frontend_dist_dir=dist)
    monkeypatch.setattr(views, "get_config", lambda: config)

    missing = client.get("/trips")
    assert missing.status_code == 404  # not built yet: a plain-text hint
    assert b"pnpm build" in missing.content

    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    response = client.get("/some/client/route")
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-cache"
    assert b"id=root" in b"".join(response.streaming_content)  # type: ignore[attr-defined]


def test_miles_are_reported_in_miles(rpc: Rpc) -> None:
    route = rpc("trips/plan", plan_body()).json()["routes"][0]
    # Chicago -> Atlanta is ~590 mi as the crow flies; any road is longer, none is absurd.
    assert 590 < route["distanceMi"] < 1100
    assert route["distanceMi"] == pytest.approx(route["checkpoints"][-1]["mile"], abs=0.1)
