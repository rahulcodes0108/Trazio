"""Weather-aware context scoring for itinerary planning."""

from __future__ import annotations

import requests

from dataclasses import dataclass, replace
from datetime import date

from app.models.destination import Destination
from app.services.destination_scorer import DestinationScore
from app.services.route_optimizer import get_coordinates
from app.services.weather_models import WeatherForecast
from app.services.weather_service import get_weather_forecast
from app.services.weather_suitability import (
    WeatherSuitability,
    calculate_weather_suitability,
)


WEATHER_SCORE_WEIGHT = 0.15


@dataclass(frozen=True)
class WeatherContext:
    """Weather intelligence associated with a destination."""

    forecast: WeatherForecast
    suitability: WeatherSuitability


def build_weather_context(
    forecast: WeatherForecast,
) -> WeatherContext:
    """Build derived weather context from a raw forecast."""

    return WeatherContext(
        forecast=forecast,
        suitability=calculate_weather_suitability(forecast),
    )


def get_destination_weather_context(
    destination: Destination,
    forecast_date: date,
) -> WeatherContext | None:
    """
    Return weather context for a destination.

    Weather is an optional intelligence signal. If coordinates are
    missing or the weather provider fails, return None so itinerary
    generation can continue normally.
    """

    try:
        # get_coordinates() expects the complete Destination object.
        coordinates = get_coordinates(destination)

        if coordinates is None:
            return None

        latitude, longitude = coordinates

        forecast = get_weather_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_date=forecast_date,
        )

        return build_weather_context(forecast)

    except (
        ValueError,
        TypeError,
        KeyError,
        requests.RequestException,
    ):
        return None


def apply_weather_score(
    destination_score: DestinationScore,
    weather_context: WeatherContext,
) -> DestinationScore:
    """Apply weather suitability to an existing destination score.

    The existing score retains 85% of its influence and weather
    contributes 15% of the final context-aware score.
    """

    weather_score = weather_context.suitability.score

    total = (
        destination_score.total_score * (1.0 - WEATHER_SCORE_WEIGHT)
        + weather_score * WEATHER_SCORE_WEIGHT
    )

    explanation = destination_score.explanation.rstrip(".")

    if weather_score >= 75:
        weather_reason = "weather conditions are favorable"
    elif weather_score >= 50:
        weather_reason = "weather conditions are moderately suitable"
    else:
        weather_reason = "weather conditions present higher travel risk"

    explanation = (
        f"{explanation}; {weather_reason} "
        f"(weather score {weather_score:.0f}/100)."
    )

    return replace(
        destination_score,
        total_score=round(total, 2),
        explanation=explanation,
    )
