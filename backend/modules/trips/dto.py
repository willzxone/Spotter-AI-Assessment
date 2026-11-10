"""The trip planner's API: one request in, every route with its risk picture out."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, Field, StringConstraints

from core.schema import ApiSchema
from modules.risk.dto import FactorKind, RiskLevelName
from modules.trips.constants import DEFAULT_CHECKPOINT_INTERVAL_MI, MAX_LOAD_LB, CheckpointIntervalMi

type Coord = tuple[float, float]  # [lon, lat], GeoJSON order


class PointIn(ApiSchema):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lon: Annotated[float, Field(ge=-180, le=180)]
    label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None


class PlanInput(ApiSchema):
    origin: PointIn
    destination: PointIn
    departure_at: AwareDatetime
    load_lb: Annotated[int, Field(ge=0, le=MAX_LOAD_LB)]
    interval_mi: CheckpointIntervalMi = DEFAULT_CHECKPOINT_INTERVAL_MI


class FactorOut(ApiSchema):
    kind: FactorKind
    level: RiskLevelName
    detail: str


class CheckpointOut(ApiSchema):
    index: int
    mile: float
    lat: float
    lon: float
    eta: datetime
    hours_from_departure: float
    level: RiskLevelName
    wind_level: RiskLevelName
    rain_level: RiskLevelName
    snow_level: RiskLevelName
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    # What set the level; empty when the level is Low.
    drivers: list[FactorOut]
    # The stretch of road this checkpoint's level is applied to when counting miles.
    covers_from_mi: float
    covers_to_mi: float


class SegmentOut(ApiSchema):
    """A run of road at one risk level, for colouring the route line."""

    level: RiskLevelName
    from_mi: float
    to_mi: float
    coords: list[Coord]


class MilesByLevelOut(ApiSchema):
    low: float
    moderate: float
    high: float
    severe: float
    no_travel: float


class RouteRiskOut(ApiSchema):
    worst: RiskLevelName
    # Mile-weighted mean of checkpoint levels: 0 = Low ... 4 = No Travel.
    average: float
    miles: MilesByLevelOut


class RouteOut(ApiSchema):
    id: str
    summary: str
    distance_mi: float
    duration_s: float
    arrival_at: datetime
    rank: int
    recommended: bool
    # One sentence: why this route is recommended, or what puts it behind the recommendation.
    verdict: str
    risk: RouteRiskOut
    geometry: list[Coord]
    segments: list[SegmentOut]
    checkpoints: list[CheckpointOut]


class HeatCellOut(ApiSchema):
    lat: float
    lon: float
    # One 0–4 risk score per hour from `HeatmapOut.start` (see risk.score): floor(score) is
    # the cell's risk level at that hour for this load.
    scores: list[float]


class HeatmapOut(ApiSchema):
    start: datetime
    hours: int
    cell_deg: float
    cells: list[HeatCellOut]


class SourcesOut(ApiSchema):
    routing: str
    weather: str


class PlanOutput(ApiSchema):
    departure_at: datetime
    load_lb: int
    interval_mi: CheckpointIntervalMi
    recommended_id: str
    # Fastest first; `rank` gives the recommendation order.
    routes: list[RouteOut]
    heatmap: HeatmapOut
    warnings: list[str]
    sources: SourcesOut
