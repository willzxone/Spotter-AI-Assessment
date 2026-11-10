# Forecasts are fetched per grid cell (~22 km x ~17 km at 40°N) and shared by every point inside
# it: weather models don't resolve finer than this, and it bounds the number of provider calls.
CELL_DEG = 0.2

# Locations per provider request.
BATCH_SIZE = 50

HOURLY_VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")

# Simulated adapter: storms present at the window start, drifting east.
# (lon, lat, eastward deg/h, radius deg, peak wind mph, peak precipitation in/hr)
SIMULATED_STORMS: tuple[tuple[float, float, float, float, float, float], ...] = (
    (-97.0, 37.5, 0.35, 2.5, 52.0, 0.8),
    (-91.0, 44.0, 0.25, 3.0, 40.0, 1.6),
    (-84.0, 33.0, 0.30, 1.8, 30.0, 0.6),
)
SIMULATED_BASE_WIND_MPH = 8.0
SIMULATED_GUST_FACTOR = 1.4
# North of this, simulated precipitation falls as snow.
SIMULATED_SNOW_LAT = 41.0
