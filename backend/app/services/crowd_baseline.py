"""Deterministic MVP crowd baseline."""

from __future__ import annotations

from datetime import date, time

from app.models.destination import Destination
from app.services.crowd_models import CrowdBaseline, CrowdLevel


def _day_factor(day_of_week: int) -> float:
    """Return expected crowd pressure for a weekday.

    Monday = 0 ... Sunday = 6.
    """
    factors = {
        0: 35.0,  # Monday
        1: 35.0,  # Tuesday
        2: 40.0,  # Wednesday
        3: 45.0,  # Thursday
        4: 55.0,  # Friday
        5: 80.0,  # Saturday
        6: 75.0,  # Sunday
    }

    return factors[day_of_week]


def _time_factor(value: time) -> float:
    """Return expected crowd pressure for time of day."""
    hour = value.hour + value.minute / 60

    if hour < 8:
        return 20.0

    if hour < 11:
        return 40.0

    if hour < 14:
        return 60.0

    if hour < 17:
        return 70.0

    if hour < 20:
        return 85.0

    if hour < 22:
        return 60.0

    return 30.0


def _category_factor(destination: Destination) -> float:
    """Return typical crowd pressure for a destination category."""
    category = getattr(
        destination.category,
        "value",
        destination.category,
    )

    factors = {
        "nature": 70.0,
        "cultural": 55.0,
        "entertainment": 75.0,
        "attraction": 65.0,
        "restaurant": 70.0,
        "shopping": 80.0,
        "accommodation": 40.0,
        "transport": 60.0,
        "other": 50.0,
    }

    return factors.get(str(category).lower(), 50.0)


def _popularity_factor(destination: Destination) -> float:
    """Use destination popularity as a crowd-pressure signal."""
    popularity = destination.popularity_score

    if popularity is None:
        return 50.0

    return max(0.0, min(100.0, float(popularity)))


def _weather_adjustment(weather_score: float | None) -> float:
    """Adjust outdoor crowd expectations using weather suitability.

    Better weather generally increases outdoor crowd pressure.
    """
    if weather_score is None:
        return 0.0

    normalized = max(0.0, min(100.0, weather_score))

    # -10 to +10 adjustment.
    return (normalized - 50.0) * 0.20


def _classify(score: float) -> CrowdLevel:
    if score < 40:
        return CrowdLevel.LOW

    if score < 70:
        return CrowdLevel.MODERATE

    return CrowdLevel.HIGH


def estimate_crowd_baseline(
    destination: Destination,
    visit_date: date,
    visit_time: time,
    weather_score: float | None = None,
) -> CrowdBaseline:
    """Estimate expected crowd pressure using deterministic MVP rules."""

    popularity = _popularity_factor(destination)
    day = _day_factor(visit_date.weekday())
    time_factor = _time_factor(visit_time)
    category = _category_factor(destination)
    weather_adjustment = _weather_adjustment(weather_score)

    score = (
        popularity * 0.30
        + day * 0.20
        + time_factor * 0.25
        + category * 0.15
        + 50.0 * 0.10
        + weather_adjustment
    )

    score = round(max(0.0, min(100.0, score)), 2)
    level = _classify(score)

    explanation_parts = [
        f"expected crowd pressure is {level.value}",
        f"based on destination popularity ({popularity:.0f}/100)",
        f"the {visit_date.strftime('%A')} pattern",
        f"the visit time ({visit_time.strftime('%H:%M')})",
        f"destination category ({category:.0f}/100 crowd tendency)",
    ]

    if weather_score is not None:
        explanation_parts.append(
            f"weather suitability ({weather_score:.0f}/100)"
        )

    explanation = "Crowd baseline: " + ", ".join(explanation_parts) + "."

    return CrowdBaseline(
        score=score,
        level=level,
        explanation=explanation,
    )