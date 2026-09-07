"""Tests for TRAZIO weather provider architecture."""

from datetime import date
from unittest.mock import Mock, patch

import pytest
import requests

from app.services.weather_models import WeatherForecast
from app.services.weather_providers.base import WeatherProvider
from app.services.weather_providers.open_meteo import OpenMeteoProvider
from app.services.weather_service import (
    get_weather_forecast,
    get_weather_provider,
)


SAMPLE_RESPONSE = {
    "latitude": 13.0404215,
    "longitude": 80.254776,
    "timezone": "Asia/Kolkata",
    "daily": {
        "time": ["2026-09-15"],
        "temperature_2m_max": [36.0],
        "temperature_2m_min": [27.4],
        "precipitation_probability_max": [57],
        "precipitation_sum": [2.4],
        "weather_code": [51],
    },
}


def test_open_meteo_provider_implements_interface():
    """Open-Meteo provider must implement the weather provider contract."""

    assert issubclass(OpenMeteoProvider, WeatherProvider)


def test_weather_forecast_model():
    """WeatherForecast should preserve normalized weather data."""

    forecast = WeatherForecast(
        latitude=13.04,
        longitude=80.25,
        timezone="Asia/Kolkata",
        forecast_date=date(2026, 9, 15),
        temperature_max_c=36.0,
        temperature_min_c=27.4,
        precipitation_probability_max=57,
        precipitation_sum_mm=2.4,
        weather_code=51,
    )

    assert forecast.latitude == 13.04
    assert forecast.longitude == 80.25
    assert forecast.timezone == "Asia/Kolkata"
    assert forecast.forecast_date == date(2026, 9, 15)
    assert forecast.temperature_max_c == 36.0
    assert forecast.temperature_min_c == 27.4
    assert forecast.precipitation_probability_max == 57
    assert forecast.precipitation_sum_mm == 2.4
    assert forecast.weather_code == 51


@patch("app.services.weather_providers.open_meteo.requests.get")
def test_open_meteo_provider_parses_response(mock_get):
    """Open-Meteo response should be converted into WeatherForecast."""

    response = Mock()
    response.json.return_value = SAMPLE_RESPONSE
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    provider = OpenMeteoProvider()

    result = provider.get_forecast(
        latitude=13.050513,
        longitude=80.2427,
        forecast_date=date(2026, 9, 15),
    )

    assert isinstance(result, WeatherForecast)
    assert result.forecast_date == date(2026, 9, 15)
    assert result.temperature_max_c == 36.0
    assert result.temperature_min_c == 27.4
    assert result.precipitation_probability_max == 57
    assert result.precipitation_sum_mm == 2.4
    assert result.weather_code == 51

    mock_get.assert_called_once()


@patch("app.services.weather_providers.open_meteo.requests.get")
def test_open_meteo_provider_sends_expected_parameters(mock_get):
    """Provider should request the required daily weather variables."""

    response = Mock()
    response.json.return_value = SAMPLE_RESPONSE
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    provider = OpenMeteoProvider()

    provider.get_forecast(
        latitude=13.050513,
        longitude=80.2427,
        forecast_date=date(2026, 9, 15),
    )

    _, kwargs = mock_get.call_args

    assert kwargs["params"]["latitude"] == 13.050513
    assert kwargs["params"]["longitude"] == 80.2427
    assert kwargs["params"]["forecast_days"] == 16
    assert kwargs["params"]["timezone"] == "auto"

    daily = kwargs["params"]["daily"]

    assert "temperature_2m_max" in daily
    assert "temperature_2m_min" in daily
    assert "precipitation_probability_max" in daily
    assert "precipitation_sum" in daily
    assert "weather_code" in daily

    assert kwargs["timeout"] == 10


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (91, 80),
        (-91, 80),
        (13, 181),
        (13, -181),
    ],
)
def test_open_meteo_provider_rejects_invalid_coordinates(
    latitude,
    longitude,
):
    """Invalid geographic coordinates should fail before making a request."""

    provider = OpenMeteoProvider()

    with pytest.raises(ValueError):
        provider.get_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_date=date(2026, 9, 15),
        )


@patch("app.services.weather_providers.open_meteo.requests.get")
def test_open_meteo_provider_rejects_missing_forecast_date(mock_get):
    """Provider should fail when the requested date is unavailable."""

    response = Mock()
    response.json.return_value = {
        **SAMPLE_RESPONSE,
        "daily": {
            **SAMPLE_RESPONSE["daily"],
            "time": ["2026-09-16"],
        },
    }
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    provider = OpenMeteoProvider()

    with pytest.raises(ValueError, match="No weather forecast available"):
        provider.get_forecast(
            latitude=13.050513,
            longitude=80.2427,
            forecast_date=date(2026, 9, 15),
        )


@patch("app.services.weather_providers.open_meteo.requests.get")
def test_open_meteo_provider_propagates_http_error(mock_get):
    """HTTP failures should not be silently swallowed."""

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("API failure")
    mock_get.return_value = response

    provider = OpenMeteoProvider()

    with pytest.raises(requests.HTTPError, match="API failure"):
        provider.get_forecast(
            latitude=13.050513,
            longitude=80.2427,
            forecast_date=date(2026, 9, 15),
        )


def test_weather_service_returns_open_meteo_provider():
    """Default TRAZIO provider should currently be Open-Meteo."""

    provider = get_weather_provider()

    assert isinstance(provider, OpenMeteoProvider)


@patch("app.services.weather_service._get_redis_client")
@patch("app.services.weather_service.get_weather_provider")
def test_weather_service_delegates_to_provider(
    mock_get_provider,
    mock_get_redis_client,
):
    """Weather service should delegate fetching to the provider on cache miss."""

    expected = WeatherForecast(
        latitude=13.04,
        longitude=80.25,
        timezone="Asia/Kolkata",
        forecast_date=date(2026, 9, 15),
        temperature_max_c=36.0,
        temperature_min_c=27.4,
        precipitation_probability_max=57,
        precipitation_sum_mm=2.4,
        weather_code=51,
    )

    # Simulate a Redis cache miss.
    redis_client = Mock()
    redis_client.get.return_value = None
    mock_get_redis_client.return_value = redis_client

    provider = Mock(spec=WeatherProvider)
    provider.get_forecast.return_value = expected
    mock_get_provider.return_value = provider

    result = get_weather_forecast(
        latitude=13.050513,
        longitude=80.2427,
        forecast_date=date(2026, 9, 15),
    )

    assert result == expected

    provider.get_forecast.assert_called_once_with(
        latitude=13.050513,
        longitude=80.2427,
        forecast_date=date(2026, 9, 15),
    )

    redis_client.setex.assert_called_once()
