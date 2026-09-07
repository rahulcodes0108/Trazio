from datetime import date, time

from app.models.destination import Destination
from app.models.trip import BudgetLevel, Trip
from app.services.destination_scorer import score_destination
from app.services.itinerary_generator import apply_crowd_score


def make_trip() -> Trip:
    return Trip(
        start_date=date(2026, 9, 12),
        start_time=time(18, 0),
        available_duration_minutes=420,
        budget_level=BudgetLevel.MID_RANGE,
        preferences={},
    )


def make_destination(
    popularity_score: float,
    category: str,
) -> Destination:
    return Destination(
        name="Test Destination",
        slug="test-destination",
        category=category,
        popularity_score=popularity_score,
        is_active=True,
    )


def test_crowd_reduces_destination_score():
    trip = make_trip()

    destination = make_destination(
        popularity_score=90,
        category="entertainment",
    )

    scored = score_destination(
        destination,
        trip,
    )

    result = apply_crowd_score(
        destination_score=scored,
        trip=trip,
    )

    assert result.total_score < scored.total_score


def test_crowd_explanation_is_preserved():
    trip = make_trip()

    destination = make_destination(
        popularity_score=90,
        category="entertainment",
    )

    scored = score_destination(
        destination,
        trip,
    )

    result = apply_crowd_score(
        destination_score=scored,
        trip=trip,
    )

    assert "Crowd baseline:" in result.explanation


def test_crowd_does_not_create_negative_score():
    trip = make_trip()

    destination = make_destination(
        popularity_score=100,
        category="shopping",
    )

    scored = score_destination(
        destination,
        trip,
    )

    result = apply_crowd_score(
        destination_score=scored,
        trip=trip,
    )

    assert 0 <= result.total_score <= 100


def test_weather_is_forwarded_to_crowd_baseline():
    trip = make_trip()

    destination = make_destination(
        popularity_score=70,
        category="nature",
    )

    scored = score_destination(
        destination,
        trip,
    )

    result = apply_crowd_score(
        destination_score=scored,
        trip=trip,
        weather_score=80,
    )

    assert "weather suitability (80/100)" in result.explanation