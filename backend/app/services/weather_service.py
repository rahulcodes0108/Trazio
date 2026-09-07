"""
Weather service with provider abstraction and Redis caching.
"""

from __future__ import annotations

import json
import os
from datetime import date

import redis

from app.services.weather_models import WeatherForecast
from app.services.weather_providers.base import WeatherProvider
from app.services.weather_providers.open_meteo import OpenMeteoProvider


WEATHER_CACHE_TTL_SECONDS = 30 * 60
WEATHER_CACHE_PREFIX = "trazio:weather:v1"


def get_weather_provider() -> WeatherProvider:
    """
    Return the configured weather provider.

    Open-Meteo is the current MVP provider.
    """
    return OpenMeteoProvider()


def _get_redis_client() -> redis.Redis:
    """
    Create a Redis client.

    REDIS_URL can be supplied through the environment.
    The Docker Compose service name is used as the default.
    """

    redis_url = os.getenv(
        "REDIS_URL",
        "redis://redis:6379/0",
    )

    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
    )


def _weather_cache_key(
    latitude: float,
    longitude: float,
    forecast_date: date,
) -> str:
    """
    Build a deterministic Redis cache key.

    Coordinates are rounded to four decimal places to avoid
    unnecessary cache fragmentation from tiny coordinate differences.
    """

    return (
        f"{WEATHER_CACHE_PREFIX}:"
        f"{latitude:.4f}:"
        f"{longitude:.4f}:"
        f"{forecast_date.isoformat()}"
    )


def _serialize_forecast(
    forecast: WeatherForecast,
) -> str:
    """
    Serialize a weather forecast for Redis.
    """

    return json.dumps(
        {
            "latitude": forecast.latitude,
            "longitude": forecast.longitude,
            "timezone": forecast.timezone,
            "forecast_date": forecast.forecast_date.isoformat(),
            "temperature_max_c": forecast.temperature_max_c,
            "temperature_min_c": forecast.temperature_min_c,
            "precipitation_probability_max": (
                forecast.precipitation_probability_max
            ),
            "precipitation_sum_mm": forecast.precipitation_sum_mm,
            "weather_code": forecast.weather_code,
        }
    )


def _deserialize_forecast(
    payload: str,
) -> WeatherForecast:
    """
    Deserialize a cached weather forecast.
    """

    data = json.loads(payload)

    return WeatherForecast(
        latitude=float(data["latitude"]),
        longitude=float(data["longitude"]),
        timezone=str(data["timezone"]),
        forecast_date=date.fromisoformat(
            data["forecast_date"]
        ),
        temperature_max_c=(
            float(data["temperature_max_c"])
            if data["temperature_max_c"] is not None
            else None
        ),
        temperature_min_c=(
            float(data["temperature_min_c"])
            if data["temperature_min_c"] is not None
            else None
        ),
        precipitation_probability_max=(
            float(data["precipitation_probability_max"])
            if data["precipitation_probability_max"] is not None
            else None
        ),
        precipitation_sum_mm=(
            float(data["precipitation_sum_mm"])
            if data["precipitation_sum_mm"] is not None
            else None
        ),
        weather_code=(
            int(data["weather_code"])
            if data["weather_code"] is not None
            else None
        ),
    )


def get_weather_forecast(
    latitude: float,
    longitude: float,
    forecast_date: date,
) -> WeatherForecast:
    """
    Get a weather forecast using Redis caching.

    Cache behavior:

    1. Try Redis.
    2. If cached, return cached forecast.
    3. Otherwise query the weather provider.
    4. Store the successful result in Redis.
    5. If Redis is unavailable, continue without caching.

    Redis is an optimization and must never become a hard dependency
    for itinerary generation.
    """

    cache_key = _weather_cache_key(
        latitude=latitude,
        longitude=longitude,
        forecast_date=forecast_date,
    )

    # -------------------------------------------------------------
    # Cache lookup
    # -------------------------------------------------------------

    try:
        redis_client = _get_redis_client()

        cached_payload = redis_client.get(
            cache_key
        )

        if cached_payload:
            return _deserialize_forecast(
                cached_payload
            )

    except (
        redis.RedisError,
        OSError,
        ValueError,
        TypeError,
    ):
        # Redis failure must not break weather retrieval.
        pass

    # -------------------------------------------------------------
    # Provider lookup
    # -------------------------------------------------------------

    provider = get_weather_provider()

    forecast = provider.get_forecast(
        latitude=latitude,
        longitude=longitude,
        forecast_date=forecast_date,
    )

    # -------------------------------------------------------------
    # Cache successful provider response
    # -------------------------------------------------------------

    try:
        redis_client = _get_redis_client()

        redis_client.setex(
            cache_key,
            WEATHER_CACHE_TTL_SECONDS,
            _serialize_forecast(forecast),
        )

    except (
        redis.RedisError,
        OSError,
        ValueError,
        TypeError,
    ):
        # Cache failure must not affect the returned forecast.
        pass

    return forecast
