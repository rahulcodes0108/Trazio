"""Tests for destination scoring."""

from app.models.destination import (
    AccessibilityLevel,
    Destination,
    DestinationCategory,
)
from app.models.trip import BudgetLevel, Trip

from app.services.destination_scorer import (
    accessibility_score,
    budget_score,
    duration_score,
    preference_score,
    rank_destinations,
    score_destination,
)


def make_trip(
    *,
    categories: list[str] | None = None,
    budget_level: BudgetLevel = BudgetLevel.MID_RANGE,
    duration: int | None = 480,
) -> Trip:
    """Create a minimal trip for scoring tests."""
    return Trip(
        id=1,
        user_id=1,
        title="Test Trip",
        start_location="Chennai",
        start_date="2026-09-15",
        budget_level=budget_level,
        transport_mode="mixed",
        preferences={
            "categories": categories or [],
        },
        available_duration_minutes=duration,
    )


def make_destination(
    *,
    destination_id: int = 1,
    category: DestinationCategory = DestinationCategory.CULTURAL,
    popularity: float = 80,
    fee: float = 100,
    visit_duration: int = 90,
    accessibility: AccessibilityLevel = (
        AccessibilityLevel.FULLY_ACCESSIBLE
    ),
) -> Destination:
    """Create a destination for scoring tests."""
    return Destination(
        id=destination_id,
        name=f"Destination {destination_id}",
        slug=f"destination-{destination_id}",
        location="POINT(80.2707 13.0827)",
        category=category,
        popularity_score=popularity,
        entry_fee=fee,
        average_visit_duration_minutes=visit_duration,
        accessibility=accessibility,
        is_active=True,
    )


def test_preference_match_scores_100():
    """Matching category should receive maximum preference score."""
    trip = make_trip(categories=["cultural"])
    destination = make_destination(
        category=DestinationCategory.CULTURAL
    )

    assert preference_score(destination, trip) == 100.0


def test_preference_mismatch_scores_zero():
    """Non-matching category should receive zero preference score."""
    trip = make_trip(categories=["nature"])
    destination = make_destination(
        category=DestinationCategory.CULTURAL
    )

    assert preference_score(destination, trip) == 0.0


def test_no_preference_filter_is_neutral():
    """No category preference should produce a neutral score."""
    trip = make_trip(categories=[])
    destination = make_destination()

    assert preference_score(destination, trip) == 50.0


def test_free_destination_gets_full_budget_score():
    """Free destinations should score perfectly for affordability."""
    trip = make_trip()
    destination = make_destination(fee=0)

    assert budget_score(destination, trip) == 100.0


def test_expensive_economy_destination_scores_zero():
    """Economy trips should reject very expensive entry fees."""
    trip = make_trip(budget_level=BudgetLevel.ECONOMY)
    destination = make_destination(fee=500)

    assert budget_score(destination, trip) == 0.0


def test_short_visit_is_duration_efficient():
    """Short visits should score highly for a long trip."""
    trip = make_trip(duration=480)
    destination = make_destination(visit_duration=45)

    assert duration_score(destination, trip) == 100.0


def test_long_visit_scores_lower():
    """Very long visits should receive a lower duration score."""
    trip = make_trip(duration=480)
    destination = make_destination(visit_duration=240)

    assert duration_score(destination, trip) == 20.0


def test_accessibility_scores():
    """Accessibility levels should map to expected scores."""
    trip = make_trip()

    fully = make_destination(
        accessibility=AccessibilityLevel.FULLY_ACCESSIBLE
    )
    partial = make_destination(
        accessibility=AccessibilityLevel.PARTIALLY_ACCESSIBLE
    )
    not_accessible = make_destination(
        accessibility=AccessibilityLevel.NOT_ACCESSIBLE
    )

    assert accessibility_score(fully) == 100.0
    assert accessibility_score(partial) == 60.0
    assert accessibility_score(not_accessible) == 20.0


def test_score_destination_is_explainable():
    """A destination score should contain component scores and an explanation."""
    trip = make_trip(categories=["cultural"])
    destination = make_destination(
        category=DestinationCategory.CULTURAL,
        popularity=90,
        fee=100,
        visit_duration=60,
    )

    result = score_destination(destination, trip)

    assert result.destination is destination
    assert result.total_score > 0
    assert result.preference_score == 100.0
    assert result.popularity_score == 90.0
    assert result.budget_score > 0
    assert result.duration_score == 100.0
    assert result.accessibility_score == 100.0
    assert "matches your interests" in result.explanation


def test_rank_destinations_orders_by_total_score():
    """Ranking should place the strongest destination first."""
    trip = make_trip(categories=["cultural"])

    strong = make_destination(
        destination_id=1,
        category=DestinationCategory.CULTURAL,
        popularity=95,
        fee=0,
        visit_duration=45,
    )

    weak = make_destination(
        destination_id=2,
        category=DestinationCategory.NATURE,
        popularity=20,
        fee=500,
        visit_duration=240,
    )

    ranked = rank_destinations(
        [weak, strong],
        trip,
    )

    assert ranked[0].destination.id == 1
    assert ranked[1].destination.id == 2
    assert ranked[0].total_score > ranked[1].total_score
