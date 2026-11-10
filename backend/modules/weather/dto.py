"""Shapes other modules receive from weather. Weather has no API surface of its own."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Reading:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True, slots=True)
class HourlySeries:
    """Hourly values for one grid cell; index 0 is the forecast window's first whole UTC hour."""

    wind_mph: tuple[float, ...]
    gust_mph: tuple[float, ...]
    rain_in_hr: tuple[float, ...]
    snow_in_hr: tuple[float, ...]

    def __len__(self) -> int:
        return len(self.wind_mph)

    def hour(self, index: int) -> Reading:
        return Reading(
            self.wind_mph[index], self.gust_mph[index], self.rain_in_hr[index], self.snow_in_hr[index]
        )

    def at(self, hours: float) -> Reading:
        """Linear interpolation `hours` after index 0, clamped to the series."""
        hours = min(max(hours, 0.0), len(self) - 1.0)
        i = min(math.floor(hours), len(self) - 2) if len(self) > 1 else 0
        f = hours - i
        if f == 0 or len(self) == 1:
            return self.hour(i)

        def lerp(values: tuple[float, ...]) -> float:
            return values[i] + (values[i + 1] - values[i]) * f

        return Reading(lerp(self.wind_mph), lerp(self.gust_mph), lerp(self.rain_in_hr), lerp(self.snow_in_hr))
