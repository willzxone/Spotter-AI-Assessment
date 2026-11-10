ROUTE_COUNT = 3
ROUTE_CACHE_TTL_S = 3600

# Shorter than this is not a trip worth routing.
MIN_TRIP_M = 1_000

# Via-point detours fill the gap when the provider returns fewer than ROUTE_COUNT alternatives.
# Each offset pushes a via point sideways from the straight-line midpoint, as a share of the
# straight-line distance, tried in this order until there are enough distinct routes.
VIA_OFFSETS = (0.15, -0.15, 0.3, -0.3)
VIA_OFFSET_CAP_M = 200_000
# A detour is a real option only if it costs at most this much time over the fastest route.
MAX_DETOUR_RATIO = 1.5

# Two routes are the same option when more than MAX_OVERLAP of one lies within
# OVERLAP_RADIUS_M of the other, measured at OVERLAP_PROBES evenly spaced points.
MAX_OVERLAP = 0.8
OVERLAP_RADIUS_M = 2_000
OVERLAP_PROBES = 60
# Coarse copy of each route used only for overlap checks.
OVERLAP_SIMPLIFY_M = 250

# Simulated adapter: straight-line legs bowed sideways (positive = right of the direction of
# travel, as a share of the leg length), each with its own average speed in m/s.
SIMULATED_STEP_M = 2_000
SIMULATED_VARIANTS: tuple[tuple[str, float, float], ...] = (
    ("Simulated direct", 0.0, 26.8),
    ("Simulated right arc", 0.08, 27.7),
    ("Simulated left arc", -0.12, 28.2),
)
SIMULATED_DETOUR_SPEED_MPS = 26.0
