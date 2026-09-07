from datetime import date

from app.services import weather_service
from app.services.weather_models import WeatherForecast


def make_forecast() -> WeatherForecast:
    return WeatherForecast(
        latitude=13.0505,
        longitude=80.2427,
        timezone="Asia/Kolkata",
        forecast_date=date(2026, 9, 15),
        temperature_max_c=36.0,
        temperature_min_c=27.4,
        precipitation_probability_max=57.0,
        precipitation_sum_mm=2.4,
        weather_code=51,
    )


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl


def test_weather_cache_key_is_deterministic():
    key = weather_service._weather_cache_key(
        13.050513,
        80.242700,
        date(2026, 9, 15),
    )

    assert key == (
        "trazio:weather:v1:"
        "13.0505:80.2427:"
        "2026-09-15"
    )


def test_weather_forecast_is_cached(monkeypatch):
    fake_redis = FakeRedis()
    forecast = make_forecast()

    provider_calls = []

    class FakeProvider:
        def get_forecast(
            self,
            latitude,
            longitude,
            forecast_date,
        ):
            provider_calls.append(1)
            return forecast

    monkeypatch.setattr(
        weather_service,
        "_get_redis_client",
        lambda: fake_redis,
    )

    monkeypatch.setattr(
        weather_service,
        "get_weather_provider",
        lambda: FakeProvider(),
    )

    first = weather_service.get_weather_forecast(
        13.0505,
        80.2427,
        date(2026, 9, 15),
    )

    second = weather_service.get_weather_forecast(
        13.0505,
        80.2427,
        date(2026, 9, 15),
    )

    assert first == forecast
    assert second == forecast
    assert len(provider_calls) == 1


def test_weather_cache_uses_expected_ttl(monkeypatch):
    fake_redis = FakeRedis()
    forecast = make_forecast()

    class FakeProvider:
        def get_forecast(
            self,
            latitude,
            longitude,
            forecast_date,
        ):
            return forecast

    monkeypatch.setattr(
        weather_service,
        "_get_redis_client",
        lambda: fake_redis,
    )

    monkeypatch.setattr(
        weather_service,
        "get_weather_provider",
        lambda: FakeProvider(),
    )

    weather_service.get_weather_forecast(
        13.0505,
        80.2427,
        date(2026, 9, 15),
    )

    key = weather_service._weather_cache_key(
        13.0505,
        80.2427,
        date(2026, 9, 15),
    )

    assert (
        fake_redis.ttls[key]
        == weather_service.WEATHER_CACHE_TTL_SECONDS
    )


def test_weather_provider_still_works_when_redis_fails(
    monkeypatch,
):
    forecast = make_forecast()

    class BrokenRedis:
        def get(self, key):
            raise weather_service.redis.RedisError(
                "Redis unavailable"
            )

        def setex(self, key, ttl, value):
            raise weather_service.redis.RedisError(
                "Redis unavailable"
            )

    class FakeProvider:
        def get_forecast(
            self,
            latitude,
            longitude,
            forecast_date,
        ):
            return forecast

    monkeypatch.setattr(
        weather_service,
        "_get_redis_client",
        lambda: BrokenRedis(),
    )

    monkeypatch.setattr(
        weather_service,
        "get_weather_provider",
        lambda: FakeProvider(),
    )

    result = weather_service.get_weather_forecast(
        13.0505,
        80.2427,
        date(2026, 9, 15),
    )

    assert result == forecast
