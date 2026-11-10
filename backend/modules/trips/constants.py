from datetime import timedelta
from typing import Literal

METERS_PER_MILE = 1609.344

# Checkpoint spacing the driver can pick, in miles.
type CheckpointIntervalMi = Literal[10, 25, 50]
CHECKPOINT_INTERVALS_MI: tuple[CheckpointIntervalMi, ...] = (10, 25, 50)
DEFAULT_CHECKPOINT_INTERVAL_MI: CheckpointIntervalMi = 25

# Route ids in order of travel time, fastest first.
ROUTE_IDS = ("A", "B", "C")

# A gross-weight cap well above any permitted load, to catch typos (lb vs kg x 1000).
MAX_LOAD_LB = 200_000

# Departures slightly in the past are "leaving now"; further ahead than this the forecast,
# and so every risk number, is too uncertain to plan against.
DEPARTURE_GRACE = timedelta(hours=1)
DEPARTURE_MAX_AHEAD = timedelta(days=7)
# Open-Meteo serves about 16 days; stay inside it with room for the trip itself.
FORECAST_HORIZON = timedelta(days=15)

# The heatmap slider covers hours 0..HEATMAP_HOURS after the departure hour.
HEATMAP_HOURS = 48
# Corridor cells are collected from points this far apart along every route.
CORRIDOR_STEP_M = 8_000

# Map geometry is simplified to this tolerance before it is sent.
GEOMETRY_SIMPLIFY_M = 40
COORD_DECIMALS = 5
