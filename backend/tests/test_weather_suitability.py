"""Tests for deterministic weather suitability intelligence."""

from datetime import date

import pytest

from app.services.weather_models import WeatherForecast
from app.services.weather_suitability import calculate_weather_suitability


def make_forecast(**overrides) -> WeatherForecast:
    """Create a forecast with sensible test defaults."""

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


def test_favorable_weather_gets_high_score():
    result = calculate_weather_suitability(make_forecast())

    assert result.score == 100.0
    assert result.risk == "low"
    assert result.suitability == "good"
    assert "favorable" in result.explanation.lower()


def test_high_rain_probability_reduces_score():
    result = calculate_weather_suitability(
        make_forecast(precipitation_probability_max=80)
    )

    assert result.score == 65.0
    assert result.risk == "medium"
    assert "very high rain probability" in result.explanation


def test_heavy_rain_reduces_score():
    result = calculate_weather_suitability(
        make_forecast(precipitation_sum_mm=25)
    )

    assert result.score == 75.0
    assert result.risk == "low"
    assert "heavy expected rainfall" in result.explanation


def test_extreme_heat_reduces_score():
    result = calculate_weather_suitability(
        make_forecast(temperature_max_c=41)
    )

    assert result.score == 75.0
    assert result.risk == "low"
    assert "extreme heat" in result.explanation


def test_thunderstorm_reduces_score():
    result = calculate_weather_suitability(
        make_forecast(weather_code=95)
    )

    assert result.score == 75.0
    assert result.risk == "low"
    assert "thunderstorm conditions" in result.explanation


def test_multiple_weather_risks_are_combined():
    result = calculate_weather_suitability(
        make_forecast(
            precipitation_probability_max=80,
            precipitation_sum_mm=25,
            temperature_max_c=41,
            weather_code=95,
        )
    )

    assert result.score == 0.0
    assert result.risk == "high"
    assert result.suitability == "poor"
    assert "very high rain probability" in result.explanation
    assert "heavy expected rainfall" in result.explanation
    assert "extreme heat" in result.explanation
    assert "thunderstorm conditions" in result.explanation


@pytest.mark.parametrize(
    ("score_inputs", "expected_risk", "expected_suitability"),
    [
        (
            {"precipitation_probability_max": 20},
            "low",
            "good",
        ),
        (
            {
                "precipitation_probability_max": 60,
                "precipitation_sum_mm": 5,
            },
            "medium",
            "moderate",
        ),
        (
            {
                "precipitation_probability_max": 80,
                "precipitation_sum_mm": 20,
                "temperature_max_c": 40,
                "weather_code": 95,
            },
            "high",
            "poor",
        ),
    ],
)
def test_risk_and_suitability_bands(
    score_inputs,
    expected_risk,
    expected_suitability,
):
    result = calculate_weather_suitability(make_forecast(**score_inputs))

    assert result.risk == expected_risk
    assert result.suitability == expected_suitability


def test_missing_weather_values_are_handled():
    result = calculate_weather_suitability(
        make_forecast(
            temperature_max_c=None,
            precipitation_probability_max=None,
            precipitation_sum_mm=None,
            weather_code=None,
        )
    )

    assert result.score == 100.0
    assert result.risk == "low"
    assert result.suitability == "good"
