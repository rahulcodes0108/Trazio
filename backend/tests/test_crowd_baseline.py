"""Tests for the MVP crowd baseline."""

from datetime import date, time

from app.models.destination import Destination
from app.services.crowd_baseline import estimate_crowd_baseline
from app.services.crowd_models import CrowdLevel


def make_destination(
    popularity_score: float,
    category: str,
) -> Destination:
    """Create an in-memory destination for crowd baseline tests."""
    return Destination(
        name="Test Destination",
        slug="test-destination",
        category=category,
        popularity_score=popularity_score,
        is_active=True,
    )


def test_popular_weekend_evening_has_high_crowd():
    destination = make_destination(
        popularity_score=95,
        category="nature",
    )

    result = estimate_crowd_baseline(
        destination=destination,
        visit_date=date(2026, 9, 12),  # Saturday
        visit_time=time(18, 0),
        weather_score=80,
    )

    assert result.score >= 70
    assert result.level == CrowdLevel.HIGH


def test_weekday_morning_has_lower_crowd():
    destination = make_destination(
        popularity_score=40,
        category="cultural",
    )

    result = estimate_crowd_baseline(
        destination=destination,
        visit_date=date(2026, 9, 14),  # Monday
        visit_time=time(9, 0),
        weather_score=70,
    )

    assert result.score < 70


def test_score_is_bounded():
    destination = make_destination(
        popularity_score=100,
        category="shopping",
    )

    result = estimate_crowd_baseline(
        destination=destination,
        visit_date=date(2026, 9, 12),
        visit_time=time(18, 0),
        weather_score=100,
    )

    assert 0 <= result.score <= 100


def test_explanation_is_present():
    destination = make_destination(
        popularity_score=80,
        category="nature",
    )

    result = estimate_crowd_baseline(
        destination=destination,
        visit_date=date(2026, 9, 12),
        visit_time=time(18, 0),
    )

    assert result.explanation
    assert "crowd baseline" in result.explanation.lower()