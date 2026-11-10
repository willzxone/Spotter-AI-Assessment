"""Risk: pure classification logic. Needs no shared services and calls nothing outside."""

from __future__ import annotations

from core.module import ServerModule
from modules.risk.router import procedures

risk_module = ServerModule(
    name="risk",
    version="1.0.0",
    requires=frozenset(),
    procedures=procedures,
)
