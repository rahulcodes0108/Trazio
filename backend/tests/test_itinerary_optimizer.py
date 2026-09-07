from types import SimpleNamespace

from app.services.destination_scorer import DestinationScore
from app.services.itinerary_optimizer import optimize_itinerary


def make_candidate(
    destination_id: int,
    score: float,
) -> DestinationScore:
    destination = SimpleNamespace(
        id=destination_id,
        popularity_score=score,
    )

    return DestinationScore(
        destination=destination,
        total_score=score,
        preference_score=score,
        popularity_score=score,
        budget_score=100.0,
        duration_score=100.0,
        accessibility_score=100.0,
        explanation="Test destination.",
    )


def test_empty_candidates():
    result = optimize_itinerary(
        candidates=[],
        travel_minutes=[[0]],
        visit_durations=[],
        entry_fees=[],
        available_minutes=480,
    )

    assert result.stops == []
    assert result.total_duration_minutes == 0
    assert result.total_cost == 0.0


def test_optimizer_selects_destinations_within_time():
    candidates = [
        make_candidate(1, 100),
        make_candidate(2, 90),
        make_candidate(3, 80),
    ]

    travel = [
        [0, 10, 20, 30],
        [10, 0, 10, 20],
        [20, 10, 0, 10],
        [30, 20, 10, 0],
    ]

    result = optimize_itinerary(
        candidates=candidates,
        travel_minutes=travel,
        visit_durations=[60, 60, 60],
        entry_fees=[0, 0, 0],
        available_minutes=150,
        max_stops=3,
    )

    assert result.total_duration_minutes <= 150
    assert len(result.stops) >= 1


def test_optimizer_respects_budget():
    candidates = [
        make_candidate(1, 100),
        make_candidate(2, 90),
        make_candidate(3, 80),
    ]

    travel = [
        [0, 5, 5, 5],
        [5, 0, 5, 5],
        [5, 5, 0, 5],
        [5, 5, 5, 0],
    ]

    result = optimize_itinerary(
        candidates=candidates,
        travel_minutes=travel,
        visit_durations=[30, 30, 30],
        entry_fees=[100, 100, 100],
        available_minutes=180,
        budget_amount=150,
        max_stops=3,
    )

    assert result.total_cost <= 150


def test_optimizer_respects_max_stops():
    candidates = [
        make_candidate(1, 100),
        make_candidate(2, 90),
        make_candidate(3, 80),
        make_candidate(4, 70),
    ]

    travel = [
        [0, 5, 5, 5, 5],
        [5, 0, 5, 5, 5],
        [5, 5, 0, 5, 5],
        [5, 5, 5, 0, 5],
        [5, 5, 5, 5, 0],
    ]

    result = optimize_itinerary(
        candidates=candidates,
        travel_minutes=travel,
        visit_durations=[20, 20, 20, 20],
        entry_fees=[0, 0, 0, 0],
        available_minutes=180,
        max_stops=2,
    )

    assert len(result.stops) <= 2


def test_optimizer_respects_available_time():
    candidates = [
        make_candidate(1, 100),
        make_candidate(2, 90),
    ]

    travel = [
        [0, 20, 20],
        [20, 0, 20],
        [20, 20, 0],
    ]

    result = optimize_itinerary(
        candidates=candidates,
        travel_minutes=travel,
        visit_durations=[100, 100],
        entry_fees=[0, 0],
        available_minutes=130,
        max_stops=2,
    )

    assert result.total_duration_minutes <= 130
