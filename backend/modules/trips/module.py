"""Trips: the planner. Owns no adapter; it composes routing, weather and risk services."""

from __future__ import annotations

from core.module import ServerModule
from modules.trips.router import procedures

trips_module = ServerModule(
    name="trips",
    version="1.0.0",
    requires=frozenset(),
    procedures=procedures,
)
