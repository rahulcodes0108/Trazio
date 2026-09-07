"""Shared weather data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WeatherForecast:
    """Normalized weather forecast used by TRAZIO."""

    latitude: float
    longitude: float
    timezone: str
    forecast_date: date
    temperature_max_c: float | None
    temperature_min_c: float | None
    precipitation_probability_max: float | None
    precipitation_sum_mm: float | None
    weather_code: int | None
