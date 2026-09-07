"""Deterministic weather suitability intelligence."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.weather_models import WeatherForecast


@dataclass(frozen=True)
class WeatherSuitability:
    """Derived weather suitability for tourism."""

    score: float
    risk: str
    suitability: str
    explanation: str


def calculate_weather_suitability(
    forecast: WeatherForecast,
) -> WeatherSuitability:
    """Convert raw weather data into an explainable tourism signal.

    This is a deterministic rule-based baseline. It does not make
    unsupported predictive claims.
    """

    score = 100.0
    reasons: list[str] = []

    precipitation_probability = forecast.precipitation_probability_max
    precipitation_sum = forecast.precipitation_sum_mm
    temperature_max = forecast.temperature_max_c
    weather_code = forecast.weather_code

    # Rain probability
    if precipitation_probability is not None:
        if precipitation_probability >= 80:
            score -= 35
            reasons.append("very high rain probability")
        elif precipitation_probability >= 60:
            score -= 25
            reasons.append("high rain probability")
        elif precipitation_probability >= 40:
            score -= 15
            reasons.append("moderate rain probability")

    # Expected rainfall amount
    if precipitation_sum is not None:
        if precipitation_sum >= 20:
            score -= 25
            reasons.append("heavy expected rainfall")
        elif precipitation_sum >= 10:
            score -= 15
            reasons.append("significant expected rainfall")
        elif precipitation_sum >= 5:
            score -= 8
            reasons.append("some expected rainfall")

    # Maximum temperature
    if temperature_max is not None:
        if temperature_max >= 40:
            score -= 25
            reasons.append("extreme heat")
        elif temperature_max >= 37:
            score -= 15
            reasons.append("high daytime temperature")
        elif temperature_max >= 34:
            score -= 7
            reasons.append("warm daytime temperature")

    # WMO weather codes.
    if weather_code is not None:
        if weather_code in {95, 96, 99}:
            score -= 25
            reasons.append("thunderstorm conditions")
        elif weather_code in {65, 67, 82}:
            score -= 15
            reasons.append("heavy precipitation conditions")
        elif weather_code in {51, 53, 55, 56, 57, 61, 63, 66}:
            score -= 8
            reasons.append("precipitation conditions")

    score = max(0.0, min(100.0, score))

    if score >= 75:
        risk = "low"
        suitability = "good"
    elif score >= 50:
        risk = "medium"
        suitability = "moderate"
    else:
        risk = "high"
        suitability = "poor"

    if reasons:
        explanation = "Weather suitability reduced because of " + ", ".join(reasons) + "."
    else:
        explanation = "Weather conditions are favorable for tourism."

    return WeatherSuitability(
        score=round(score, 2),
        risk=risk,
        suitability=suitability,
        explanation=explanation,
    )
