from __future__ import annotations

from modules.geocoding.dto import Place

SEARCH_CACHE_TTL_S = 24 * 3600

# Offline gazetteer for the simulated adapter: major US freight hubs.
_HUBS: tuple[tuple[str, str, float, float], ...] = (
    ("Atlanta", "Georgia", 33.7490, -84.3880),
    ("Albuquerque", "New Mexico", 35.0844, -106.6504),
    ("Billings", "Montana", 45.7833, -108.5007),
    ("Boston", "Massachusetts", 42.3601, -71.0589),
    ("Charlotte", "North Carolina", 35.2271, -80.8431),
    ("Chicago", "Illinois", 41.8781, -87.6298),
    ("Cheyenne", "Wyoming", 41.1400, -104.8202),
    ("Dallas", "Texas", 32.7767, -96.7970),
    ("Denver", "Colorado", 39.7392, -104.9903),
    ("Des Moines", "Iowa", 41.5868, -93.6250),
    ("Detroit", "Michigan", 42.3314, -83.0458),
    ("El Paso", "Texas", 31.7619, -106.4850),
    ("Houston", "Texas", 29.7604, -95.3698),
    ("Indianapolis", "Indiana", 39.7684, -86.1581),
    ("Jacksonville", "Florida", 30.3322, -81.6557),
    ("Kansas City", "Missouri", 39.0997, -94.5786),
    ("Las Vegas", "Nevada", 36.1699, -115.1398),
    ("Los Angeles", "California", 34.0522, -118.2437),
    ("Louisville", "Kentucky", 38.2527, -85.7585),
    ("Memphis", "Tennessee", 35.1495, -90.0490),
    ("Miami", "Florida", 25.7617, -80.1918),
    ("Minneapolis", "Minnesota", 44.9778, -93.2650),
    ("Nashville", "Tennessee", 36.1627, -86.7816),
    ("New Orleans", "Louisiana", 29.9511, -90.0715),
    ("New York", "New York", 40.7128, -74.0060),
    ("Oklahoma City", "Oklahoma", 35.4676, -97.5164),
    ("Omaha", "Nebraska", 41.2565, -95.9345),
    ("Philadelphia", "Pennsylvania", 39.9526, -75.1652),
    ("Phoenix", "Arizona", 33.4484, -112.0740),
    ("Pittsburgh", "Pennsylvania", 40.4406, -79.9959),
    ("Portland", "Oregon", 45.5152, -122.6784),
    ("Salt Lake City", "Utah", 40.7608, -111.8910),
    ("San Antonio", "Texas", 29.4241, -98.4936),
    ("Seattle", "Washington", 47.6062, -122.3321),
    ("St. Louis", "Missouri", 38.6270, -90.1994),
)

GAZETTEER: tuple[Place, ...] = tuple(
    Place(
        id=f"sim-{name.lower().replace(' ', '-').replace('.', '')}",
        name=name,
        label=f"{name}, {state}, United States",
        lat=lat,
        lon=lon,
        kind="city",
    )
    for name, state, lat, lon in _HUBS
)
