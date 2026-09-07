"""Destination scoring for context-aware itinerary planning."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.destination import Destination
from app.models.trip import BudgetLevel, Trip


@dataclass(frozen=True)
class DestinationScore:
    """Scored destination with explainable component scores."""

    destination: Destination
    total_score: float
    preference_score: float
    popularity_score: float
    budget_score: float
    duration_score: float
    accessibility_score: float
    explanation: str


# Relative weights for the Phase 5 baseline.
# All component scores are normalized to 0-100.
SCORING_WEIGHTS = {
    "preference": 0.35,
    "popularity": 0.20,
    "budget": 0.20,
    "duration": 0.15,
    "accessibility": 0.10,
}


def _requested_categories(trip: Trip) -> set[str]:
    """Extract normalized requested categories from trip preferences."""
    preferences = trip.preferences or {}
    categories = preferences.get("categories")

    if not isinstance(categories, list):
        return set()

    return {
        str(category).strip().lower()
        for category in categories
        if category
    }


def preference_score(destination: Destination, trip: Trip) -> float:
    """Score how well a destination matches requested categories."""
    requested = _requested_categories(trip)

    if not requested:
        return 50.0

    category = getattr(
        destination.category,
        "value",
        destination.category,
    )

    if str(category).strip().lower() in requested:
        return 100.0

    return 0.0


def popularity_score(destination: Destination) -> float:
    """Normalize destination popularity to a 0-100 score."""
    value = destination.popularity_score or 0.0
    return max(0.0, min(100.0, float(value)))


def budget_score(destination: Destination, trip: Trip) -> float:
    """Score destination affordability for the selected budget."""
    fee = float(destination.entry_fee or 0.0)

    if fee == 0:
        return 100.0

    budget_level = getattr(
        trip.budget_level,
        "value",
        trip.budget_level,
    )

    # Baseline affordability bands.
    limits = {
        BudgetLevel.ECONOMY.value: 500.0,
        BudgetLevel.MID_RANGE.value: 2000.0,
        BudgetLevel.LUXURY.value: float("inf"),
        BudgetLevel.CUSTOM.value: float("inf"),
    }

    limit = limits.get(str(budget_level), 2000.0)

    if limit == float("inf"):
        return 100.0

    if fee >= limit:
        return 0.0

    return max(0.0, 100.0 * (1.0 - fee / limit))


def duration_score(destination: Destination, trip: Trip) -> float:
    """Score destinations based on practical visit duration."""
    visit_minutes = (
        destination.average_visit_duration_minutes or 60
    )

    available = trip.available_duration_minutes

    if not available:
        return 50.0

    # Destinations taking more than half the available trip
    # receive a progressively lower score.
    ratio = visit_minutes / available

    if ratio <= 0.15:
        return 100.0

    if ratio >= 0.50:
        return 20.0

    return max(
        20.0,
        100.0 - ((ratio - 0.15) / 0.35) * 80.0,
    )


def accessibility_score(destination: Destination) -> float:
    """Score destination accessibility."""
    accessibility = getattr(
        destination.accessibility,
        "value",
        destination.accessibility,
    )

    scores = {
        "fully_accessible": 100.0,
        "partially_accessible": 60.0,
        "not_accessible": 20.0,
        "unknown": 50.0,
    }

    return scores.get(str(accessibility), 50.0)


def score_destination(
    destination: Destination,
    trip: Trip,
) -> DestinationScore:
    """Calculate an explainable hybrid score for a destination."""
    preference = preference_score(destination, trip)
    popularity = popularity_score(destination)
    budget = budget_score(destination, trip)
    duration = duration_score(destination, trip)
    accessibility = accessibility_score(destination)

    total = (
        preference * SCORING_WEIGHTS["preference"]
        + popularity * SCORING_WEIGHTS["popularity"]
        + budget * SCORING_WEIGHTS["budget"]
        + duration * SCORING_WEIGHTS["duration"]
        + accessibility * SCORING_WEIGHTS["accessibility"]
    )

    reasons: list[str] = []

    if preference >= 100:
        reasons.append("matches your interests")
    elif preference == 50:
        reasons.append("no specific interest filter was provided")

    if popularity >= 75:
        reasons.append("is highly popular")

    if budget >= 75:
        reasons.append("fits the selected budget")

    if duration >= 75:
        reasons.append("has an efficient visit duration")

    if accessibility >= 75:
        reasons.append("has strong accessibility")

    explanation = "Selected because it " + ", ".join(reasons) + "."

    return DestinationScore(
        destination=destination,
        total_score=round(total, 2),
        preference_score=round(preference, 2),
        popularity_score=round(popularity, 2),
        budget_score=round(budget, 2),
        duration_score=round(duration, 2),
        accessibility_score=round(accessibility, 2),
        explanation=explanation,
    )


def rank_destinations(
    destinations: list[Destination],
    trip: Trip,
) -> list[DestinationScore]:
    """Rank destinations from highest to lowest hybrid score."""
    scored = [
        score_destination(destination, trip)
        for destination in destinations
    ]

    return sorted(
        scored,
        key=lambda item: (
            item.total_score,
            item.destination.popularity_score or 0.0,
            -item.destination.id,
        ),
        reverse=True,
    )
