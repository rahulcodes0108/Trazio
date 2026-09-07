"""Tests for weather-aware destination context scoring."""

from datetime import date

from app.models.destination import Destination
from app.models.trip import Trip
from app.services.destination_scorer import score_destination
from app.services.weather_context import (
    WEATHER_SCORE_WEIGHT,
    apply_weather_score,
    build_weather_context,
)
from app.services.weather_models import WeatherForecast


def make_forecast(**overrides):
    values = {
        "latitude": 13.05,
        "longitude": 80.24,
        "timezone": "Asia/Kolkata",
        "forecast_date": date(2026, 9, 15),
        "temperature_max_c": 30.0,
        "temperature_min_c": 24.0,
        "precipitation_probability_max": 10,
        "precipitation_sum_mm": 0.0,
        "weather_code": 1,
    }

    values.update(overrides)
    return WeatherForecast(**values)


def make_destination():
    return Destination(
        id=999,
        name="Weather Test Destination",
        slug="weather-test-destination",
        category="nature",
        popularity_score=80,
        entry_fee=0,
        average_visit_duration_minutes=60,
        is_active=True,
    )


def make_trip():
    return Trip(
        id=999,
        user_id=1,
        title="Weather Test Trip",
        start_location="Chennai",
        start_date=date(2026, 9, 15),
        available_duration_minutes=480,
        budget_level="mid_range",
        preferences={"categories": ["nature"]},
    )


def test_build_weather_context():
    forecast = make_forecast()

    context = build_weather_context(forecast)

    assert context.forecast == forecast
    assert context.suitability.score == 100.0
    assert context.suitability.risk == "low"


def test_favorable_weather_increases_or_preserves_score():
    destination_score = score_destination(
        make_destination(),
        make_trip(),
    )

    context = build_weather_context(make_forecast())

    result = apply_weather_score(
        destination_score,
        context,
    )

    assert result.total_score >= destination_score.total_score
    assert "weather conditions are favorable" in result.explanation


def test_poor_weather_reduces_score():
    destination_score = score_destination(
        make_destination(),
        make_trip(),
    )

    context = build_weather_context(
        make_forecast(
            precipitation_probability_max=90,
            precipitation_sum_mm=25,
            temperature_max_c=41,
            weather_code=95,
        )
    )

    result = apply_weather_score(
        destination_score,
        context,
    )

    assert result.total_score < destination_score.total_score
    assert "higher travel risk" in result.explanation


def test_weather_weight_is_15_percent():
    assert WEATHER_SCORE_WEIGHT == 0.15


def test_weather_score_uses_weighted_combination():
    destination_score = score_destination(
        make_destination(),
        make_trip(),
    )

    context = build_weather_context(
        make_forecast(
            precipitation_probability_max=60,
            precipitation_sum_mm=5,
        )
    )

    result = apply_weather_score(
        destination_score,
        context,
    )

    expected = (
        destination_score.total_score * 0.85
        + context.suitability.score * 0.15
    )

    assert result.total_score == round(expected, 2)


def test_moderate_weather_is_explained():
    destination_score = score_destination(
        make_destination(),
        make_trip(),
    )

    context = build_weather_context(
        make_forecast(
            precipitation_probability_max=60,
            precipitation_sum_mm=5,
        )
    )

    result = apply_weather_score(
        destination_score,
        context,
    )

    assert "moderately suitable" in result.explanation
