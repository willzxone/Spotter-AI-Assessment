"""The module registry: the one place that knows which modules exist.

Order is boot order. Modules other modules call (routing, weather, risk) come before the
ones that call them, so every service is configured before anything can reach it.
To add a module, write `modules/<name>/module.py` and list it here; nothing else changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.module import ServerModule


def load_registry() -> tuple[ServerModule, ...]:
    # Imported lazily so importing `modules` never drags in Django before settings load.
    from modules.geocoding.module import geocoding_module
    from modules.risk.module import risk_module
    from modules.routing.module import routing_module
    from modules.trips.module import trips_module
    from modules.weather.module import weather_module

    return (
        risk_module,
        routing_module,
        weather_module,
        geocoding_module,
        trips_module,
    )
