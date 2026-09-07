"""Tests for itinerary route optimization."""

from app.models.destination import Destination
from app.services.route_optimizer import (
    haversine_distance_km,
    optimize_route,
)


def test_haversine_distance():
    """Distance between identical coordinates should be zero."""
    distance = haversine_distance_km(
        13.0500,
        80.2824,
        13.0500,
        80.2824,
    )

    assert distance == 0


def test_optimize_route_empty():
    """Empty destination list should return an empty route."""
    assert optimize_route([]) == []


def test_optimize_route_orders_destinations():
    """Optimizer should return every destination exactly once."""
    destinations = [
        Destination(
            id=1,
            name="A",
            slug="a",
            location="POINT(80.2824 13.0500)",
            popularity_score=90,
        ),
        Destination(
            id=2,
            name="B",
            slug="b",
            location="POINT(80.2690 12.9998)",
            popularity_score=80,
        ),
        Destination(
            id=3,
            name="C",
            slug="c",
            location="POINT(80.2598 12.9940)",
            popularity_score=70,
        ),
    ]

    route = optimize_route(destinations)

    assert len(route) == 3
    assert {destination.id for destination in route} == {1, 2, 3}
    assert route[0].id == 1
