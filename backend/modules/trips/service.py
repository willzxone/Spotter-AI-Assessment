"""Trip planning: routes, weather at every checkpoint's ETA, risk, ranking and the heatmap.

Talks to the other modules only through their services: routing for the roads, weather for
forecasts, risk for classification. It owns no adapter and no state of its own.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from common.geo import LonLat, locate, simplify
from core.errors import bad_request
from modules.risk import service as risk
from modules.risk.dto import Assessment, Conditions, RiskLevel
from modules.routing import service as routing
from modules.routing.dto import RoadRoute
from modules.trips import ranking
from modules.trips.checkpoints import Checkpoint, place
from modules.trips.constants import (
    COORD_DECIMALS,
    CORRIDOR_STEP_M,
    DEPARTURE_GRACE,
    DEPARTURE_MAX_AHEAD,
    FORECAST_HORIZON,
    GEOMETRY_SIMPLIFY_M,
    HEATMAP_HOURS,
    METERS_PER_MILE,
    ROUTE_IDS,
)
from modules.trips.dto import (
    CheckpointOut,
    Coord,
    FactorOut,
    HeatCellOut,
    HeatmapOut,
    MilesByLevelOut,
    PlanInput,
    PlanOutput,
    RouteOut,
    RouteRiskOut,
    SegmentOut,
    SourcesOut,
)
from modules.weather import service as weather
from modules.weather.constants import CELL_DEG
from modules.weather.dto import HourlySeries, Reading


def plan(payload: PlanInput, now: datetime | None = None) -> PlanOutput:
    now = now or datetime.now(UTC)
    departure = payload.departure_at.astimezone(UTC)
    _check_departure(departure, now)

    origin: LonLat = (payload.origin.lon, payload.origin.lat)
    destination: LonLat = (payload.destination.lon, payload.destination.lat)
    roads = sorted(routing.plan(origin, destination), key=lambda r: r.duration_s)[: len(ROUTE_IDS)]

    interval_m = payload.interval_mi * METERS_PER_MILE
    checkpoints = [place(road, interval_m) for road in roads]

    # One forecast window for everything: from the departure's whole hour to the last
    # arrival, and never shorter than the heatmap slider.
    start = departure.replace(minute=0, second=0, microsecond=0)
    offset_h = (departure - start).total_seconds() / 3600
    longest_h = max(road.duration_s for road in roads) / 3600
    hours = max(HEATMAP_HOURS, math.ceil(offset_h + longest_h) + 1)
    if start + timedelta(hours=hours) > now + FORECAST_HORIZON:
        raise bad_request(
            "This trip ends beyond the forecast horizon. Pick an earlier departure.",
            field="departureAt",
        )

    checkpoint_cells = {weather.cell_of(cp.coord) for cps in checkpoints for cp in cps}
    corridor = _corridor_cells(roads)
    series = weather.forecast(checkpoint_cells | corridor, start, hours)

    routes: list[RouteOut] = []
    summaries: list[ranking.RouteRisk] = []
    for route_id, road, cps in zip(ROUTE_IDS, roads, checkpoints, strict=False):
        assessed: list[tuple[Checkpoint, Reading, Assessment]] = []
        for cp in cps:
            # The weather where the truck will be, at the hour it gets there.
            reading = series[weather.cell_of(cp.coord)].at(offset_h + cp.eta_s / 3600)
            assessed.append((cp, reading, risk.assess(_conditions(reading), payload.load_lb)))
        summary = ranking.summarize(
            route_id,
            [(a.level, (cp.covers_to_m - cp.covers_from_m) / METERS_PER_MILE) for cp, _, a in assessed],
            road.duration_s,
        )
        summaries.append(summary)
        routes.append(_route_out(route_id, road, departure, offset_h, assessed, summary))

    ranked = ranking.rank(summaries)
    order = {r.id: i + 1 for i, r in enumerate(ranked)}
    verdicts = ranking.verdicts(ranked)
    routes = [
        route.model_copy(
            update={
                "rank": order[route.id],
                "recommended": order[route.id] == 1,
                "verdict": verdicts[route.id],
            }
        )
        for route in routes
    ]

    return PlanOutput(
        departure_at=departure,
        load_lb=payload.load_lb,
        interval_mi=payload.interval_mi,
        recommended_id=ranked[0].id,
        routes=routes,
        heatmap=_heatmap(series, corridor, start, hours, payload.load_lb),
        warnings=_warnings(ranked, len(roads)),
        sources=SourcesOut(routing=routing.source(), weather=weather.source()),
    )


def _check_departure(departure: datetime, now: datetime) -> None:
    if departure < now - DEPARTURE_GRACE:
        raise bad_request("Departure time is in the past.", field="departureAt")
    if departure > now + DEPARTURE_MAX_AHEAD:
        days = DEPARTURE_MAX_AHEAD.days
        raise bad_request(
            f"Departure must be within the next {days} days; forecasts further out are not reliable.",
            field="departureAt",
        )


def _conditions(reading: Reading) -> Conditions:
    return Conditions(wind_mph=reading.wind_mph, rain_in_hr=reading.rain_in_hr, snow_in_hr=reading.snow_in_hr)


def _corridor_cells(roads: Iterable[RoadRoute]) -> set[LonLat]:
    """Every forecast cell the routes pass through, sampled every CORRIDOR_STEP_M."""
    cells: set[LonLat] = set()
    for road in roads:
        steps = max(1, math.ceil(road.distance_m / CORRIDOR_STEP_M))
        for k in range(steps + 1):
            at = min(k * CORRIDOR_STEP_M, road.distance_m)
            cells.add(weather.cell_of(locate(road.coords, road.cumulative_m, at).coord))
    return cells


def _round(coord: LonLat) -> Coord:
    return (round(coord[0], COORD_DECIMALS), round(coord[1], COORD_DECIMALS))


def _route_out(
    route_id: str,
    road: RoadRoute,
    departure: datetime,
    offset_h: float,
    assessed: Sequence[tuple[Checkpoint, Reading, Assessment]],
    summary: ranking.RouteRisk,
) -> RouteOut:
    keep = simplify(road.coords, GEOMETRY_SIMPLIFY_M)
    checkpoints_out = [
        CheckpointOut(
            index=cp.index,
            mile=round(cp.at_m / METERS_PER_MILE, 1),
            lat=round(cp.coord[1], COORD_DECIMALS),
            lon=round(cp.coord[0], COORD_DECIMALS),
            eta=departure + timedelta(seconds=cp.eta_s),
            hours_from_departure=round(cp.eta_s / 3600, 2),
            level=a.level.api_name,
            wind_level=a.wind.api_name,
            rain_level=a.rain.api_name,
            snow_level=a.snow.api_name,
            wind_mph=round(reading.wind_mph, 1),
            gust_mph=round(reading.gust_mph, 1),
            rain_in_hr=round(reading.rain_in_hr, 3),
            snow_in_hr=round(reading.snow_in_hr, 3),
            drivers=[FactorOut(kind=f.kind, level=f.level.api_name, detail=f.detail) for f in a.drivers],
            covers_from_mi=round(cp.covers_from_m / METERS_PER_MILE, 2),
            covers_to_mi=round(cp.covers_to_m / METERS_PER_MILE, 2),
        )
        for cp, reading, a in assessed
    ]
    return RouteOut(
        id=route_id,
        summary=road.summary,
        distance_mi=round(road.distance_m / METERS_PER_MILE, 1),
        duration_s=round(road.duration_s),
        arrival_at=departure + timedelta(seconds=road.duration_s),
        rank=0,
        recommended=False,
        verdict="",
        risk=RouteRiskOut(
            worst=summary.worst.api_name,
            average=round(summary.average, 2),
            miles=MilesByLevelOut(
                low=round(summary.miles[RiskLevel.LOW], 1),
                moderate=round(summary.miles[RiskLevel.MODERATE], 1),
                high=round(summary.miles[RiskLevel.HIGH], 1),
                severe=round(summary.miles[RiskLevel.SEVERE], 1),
                no_travel=round(summary.miles[RiskLevel.NO_TRAVEL], 1),
            ),
        ),
        geometry=[_round(road.coords[i]) for i in keep],
        segments=_segments(road, keep, [(cp, a.level) for cp, _, a in assessed]),
        checkpoints=checkpoints_out,
    )


def _segments(
    road: RoadRoute, keep: Sequence[int], levels: Sequence[tuple[Checkpoint, RiskLevel]]
) -> list[SegmentOut]:
    """Merge neighbouring checkpoints at the same level into runs, each with its own line."""
    runs: list[tuple[RiskLevel, float, float]] = []
    for cp, level in levels:
        if runs and runs[-1][0] == level:
            runs[-1] = (level, runs[-1][1], cp.covers_to_m)
        else:
            runs.append((level, cp.covers_from_m, cp.covers_to_m))

    out: list[SegmentOut] = []
    for level, from_m, to_m in runs:
        coords: list[LonLat] = [locate(road.coords, road.cumulative_m, from_m).coord]
        coords += [road.coords[i] for i in keep if from_m < road.cumulative_m[i] < to_m]
        coords.append(locate(road.coords, road.cumulative_m, to_m).coord)
        out.append(
            SegmentOut(
                level=level.api_name,
                from_mi=round(from_m / METERS_PER_MILE, 2),
                to_mi=round(to_m / METERS_PER_MILE, 2),
                coords=[_round(c) for c in coords],
            )
        )
    return out


def _heatmap(
    series: dict[LonLat, HourlySeries], cells: Iterable[LonLat], start: datetime, hours: int, load_lb: int
) -> HeatmapOut:
    out: list[HeatCellOut] = []
    for cell in sorted(cells):
        s = series[cell]
        scores = [round(risk.score(_conditions(s.hour(h)), load_lb), 2) for h in range(hours + 1)]
        out.append(HeatCellOut(lat=cell[1], lon=cell[0], scores=scores))
    return HeatmapOut(start=start, hours=hours, cell_deg=CELL_DEG, cells=out)


def _warnings(ranked: Sequence[ranking.RouteRisk], found: int) -> list[str]:
    out: list[str] = []
    if found < len(ROUTE_IDS):
        out.append(f"Only {found} distinct route{'s' if found != 1 else ''} found between these places.")
    best = ranked[0]
    if all(r.miles[RiskLevel.NO_TRAVEL] > 0 for r in ranked):
        out.append("Every route crosses No Travel conditions. Consider delaying departure.")
    elif best.miles[RiskLevel.SEVERE] > 0:
        out.append(
            f"Even the recommended route has {best.miles[RiskLevel.SEVERE]:.0f} mi of Severe conditions."
        )
    return out
