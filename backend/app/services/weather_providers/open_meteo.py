"""Open-Meteo weather provider."""

from __future__ import annotations

from datetime import date
from typing import Any

import requests

from app.services.weather_models import WeatherForecast
from app.services.weather_providers.base import WeatherProvider


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoProvider(WeatherProvider):
    """Weather provider backed by Open-Meteo."""

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_date: date,
    ) -> WeatherForecast:
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        response = requests.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": (
                    "temperature_2m_max,"
                    "temperature_2m_min,"
                    "precipitation_probability_max,"
                    "precipitation_sum,"
                    "weather_code"
                ),
                "forecast_days": 16,
                "timezone": "auto",
            },
            timeout=10,
        )

        response.raise_for_status()

        data: dict[str, Any] = response.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])

        if forecast_date.isoformat() not in dates:
            raise ValueError(
                f"No weather forecast available for {forecast_date.isoformat()}"
            )

        index = dates.index(forecast_date.isoformat())

        def get_daily_value(key: str) -> Any:
            values = daily.get(key, [])
            return values[index] if index < len(values) else None

        return WeatherForecast(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            timezone=str(data["timezone"]),
            forecast_date=forecast_date,
            temperature_max_c=get_daily_value("temperature_2m_max"),
            temperature_min_c=get_daily_value("temperature_2m_min"),
            precipitation_probability_max=get_daily_value(
                "precipitation_probability_max"
            ),
            precipitation_sum_mm=get_daily_value("precipitation_sum"),
            weather_code=get_daily_value("weather_code"),
        )
