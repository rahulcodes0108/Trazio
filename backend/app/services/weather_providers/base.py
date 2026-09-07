"""Weather provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from app.services.weather_models import WeatherForecast


class WeatherProvider(ABC):
    """Interface implemented by weather data providers."""

    @abstractmethod
    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_date: date,
    ) -> WeatherForecast:
        """Return weather forecast for a destination and date."""
        raise NotImplementedError
