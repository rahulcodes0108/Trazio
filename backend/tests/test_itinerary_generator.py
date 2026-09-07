"""Tests for itinerary generation pipeline and intelligence functions."""

from datetime import date, time
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.destination import Destination, DestinationCategory, AccessibilityLevel
from app.services.mapbox_service import MapboxServiceError
from app.models.trip import Trip, TripStatus, BudgetLevel, TransportMode
from app.models.user import User, UserStatus
from app.services.destination_scorer import DestinationScore, rank_destinations
from app.services.itinerary_generator import (
    _apply_personalization,
    _apply_weather_and_crowd,
    _execute_itinerary_planning,
    _rank_candidates_with_intelligence,
    _build_generation_pipeline,
    ItineraryGenerationError,
    DEFAULT_VISIT_DURATION_MINUTES,
    MAX_MAPBOX_DESTINATIONS,
)
from app.services.personalization import PersonalizationProfile
from app.services.weather_context import WeatherContext
from app.services.weather_suitability import WeatherSuitability


def make_mock_destination(
    id: int = 1,
    name: str = "Test Destination",
    popularity_score: float = 75.0,
    entry_fee: float = 100.0,
    average_visit_duration_minutes: int = 120,
    category: DestinationCategory = DestinationCategory.ATTRACTION,
    accessibility: AccessibilityLevel = AccessibilityLevel.FULLY_ACCESSIBLE,
    location_wkt: str = "POINT(80.2824 13.0500)",
    city: str = "Bangalore",
    country: str = "India",
) -> Destination:
    """Create a mock destination for testing."""
    destination = Destination()
    destination.id = id
    destination.name = name
    destination.popularity_score = popularity_score
    destination.entry_fee = entry_fee
    destination.average_visit_duration_minutes = average_visit_duration_minutes
    destination.category = category
    destination.accessibility = accessibility
    destination.location = location_wkt
    destination.city = city
    destination.country = country
    destination.is_active = True
    return destination


def make_mock_trip(
    user_id: int | None = 1,
    start_location: str = "Bangalore",
    start_date: str = "2023-07-01",
    available_duration_minutes: int = 480,
    budget_level: BudgetLevel = BudgetLevel.MID_RANGE,
    transport_mode: TransportMode = TransportMode.MIXED,
    budget_amount: float = 2000.0,
    start_time: time | None = time(9, 0),
    preferences: dict | None = None,
) -> Trip:
    """Create a mock trip for testing."""
    trip = Trip()
    trip.user_id = user_id
    trip.start_location = start_location
    trip.start_date = date.fromisoformat(start_date)
    trip.available_duration_minutes = available_duration_minutes
    trip.budget_level = budget_level
    trip.transport_mode = transport_mode
    trip.budget_amount = budget_amount
    trip.start_time = start_time
    trip.preferences = preferences or {}
    trip.status = TripStatus.PLANNING
    return trip


def make_mock_user(id: int = 1) -> User:
    """Create a mock user for testing."""
    user = User()
    user.id = id
    user.email = "test@example.com"
    user.username = "testuser"
    user.full_name = "Test User"
    user.status = UserStatus.ACTIVE
    return user


def make_mock_weather_context(score: float = 80.0) -> WeatherContext:
    """Create a mock weather context for testing."""
    from app.services.weather_models import WeatherForecast

    # Create mock forecast
    forecast = WeatherForecast(
        latitude=13.0500,
        longitude=80.2824,
        timezone="Asia/Kolkata",
        forecast_date=date(2023, 7, 1),
        temperature_max_c=25.0,
        temperature_min_c=20.0,
        precipitation_probability_max=0.0,
        precipitation_sum_mm=0.0,
        weather_code=800,
    )

    from app.services.weather_suitability import calculate_weather_suitability
    suitability = calculate_weather_suitability(forecast)

    return WeatherContext(forecast=forecast, suitability=suitability)


def make_mock_personalization_profile() -> PersonalizationProfile:
    """Create a mock personalization profile for testing."""
    return PersonalizationProfile(
        category_affinity={"attraction": 0.8, "cultural": 0.6},
        rated_destination_ids=frozenset([1, 2]),
        interaction_count=5,
    )


class TestApplyPersonalization:
    """Tests for the _apply_personalization function."""

    def test_apply_personalization_basic(self):
        """Test basic personalization application."""
        destination = make_mock_destination()
        trip = make_mock_trip()
        profile = make_mock_personalization_profile()

        # Create a base destination score
        base_score = DestinationScore(
            destination=destination,
            total_score=80.0,
            preference_score=70.0,
            popularity_score=85.0,
            budget_score=90.0,
            duration_score=75.0,
            accessibility_score=100.0,
            explanation="Selected because it is highly popular, fits the selected budget.",
        )

        with patch('app.services.itinerary_generator.hybrid_personalization_score') as mock_hps, \
             patch('app.services.itinerary_generator.personalization_explanation') as mock_pe:

            mock_hps.return_value = 90.0
            mock_pe.return_value = "Personalized because it matches categories you have rated highly."

            result = _apply_personalization(base_score, destination, trip, profile)

            # Check that personalization score was applied
            expected_score = round(80.0 * 0.65 + 90.0 * 0.35, 2)
            assert result.total_score == expected_score

            # Check that explanation was updated
            assert "matches categories you have rated highly" in result.explanation

    def test_apply_personalization_no_reason(self):
        """Test personalization with no personalization reason."""
        destination = make_mock_destination()
        trip = make_mock_trip()
        profile = make_mock_personalization_profile()

        base_score = DestinationScore(
            destination=destination,
            total_score=80.0,
            preference_score=70.0,
            popularity_score=85.0,
            budget_score=90.0,
            duration_score=75.0,
            accessibility_score=100.0,
            explanation="Selected because it is highly popular.",
        )

        with patch('app.services.itinerary_generator.hybrid_personalization_score') as mock_hps, \
             patch('app.services.itinerary_generator.personalization_explanation') as mock_pe:

            mock_hps.return_value = 70.0
            mock_pe.return_value = None  # No personalization reason

            result = _apply_personalization(base_score, destination, trip, profile)

            # Check that explanation remains unchanged
            assert result.explanation == base_score.explanation


class TestApplyWeatherAndCrowd:
    """Tests for the _apply_weather_and_crowd function."""

    def test_apply_weather_and_crowd_both_available(self):
        """Test applying both weather and crowd intelligence."""
        destination = make_mock_destination()
        trip = make_mock_trip()
        weather_context = make_mock_weather_context()

        base_score = DestinationScore(
            destination=destination,
            total_score=80.0,
            preference_score=70.0,
            popularity_score=85.0,
            budget_score=90.0,
            duration_score=75.0,
            accessibility_score=100.0,
            explanation="Selected because it is highly popular.",
        )

        with patch('app.services.itinerary_generator.apply_weather_score') as mock_aws, \
             patch('app.services.itinerary_generator.apply_crowd_score') as mock_acs:

            # Mock the weather and crowd functions
            weather_result = replace(base_score, total_score=82.0, explanation="Selected because it is highly popular; weather conditions are favorable (weather score 80/100).")
            crowd_result = replace(weather_result, total_score=78.0, explanation="Selected because it is highly popular; weather conditions are favorable (weather score 80/100); Crowd baseline: expected crowd pressure is moderate.")

            mock_aws.return_value = weather_result
            mock_acs.return_value = crowd_result

            result = _apply_weather_and_crowd(base_score, destination, trip, weather_context)

            # Check that both functions were called
            mock_aws.assert_called_once()
            mock_acs.assert_called_once()

            # Check that the result is the crowd result
            assert result == crowd_result

    def test_apply_weather_and_crowd_no_weather(self):
        """Test applying weather and crowd when weather context is None."""
        destination = make_mock_destination()
        trip = make_mock_trip()

        base_score = DestinationScore(
            destination=destination,
            total_score=80.0,
            preference_score=70.0,
            popularity_score=85.0,
            budget_score=90.0,
            duration_score=75.0,
            accessibility_score=100.0,
            explanation="Selected because it is highly popular.",
        )

        with patch('app.services.itinerary_generator.apply_weather_score') as mock_aws, \
             patch('app.services.itinerary_generator.apply_crowd_score') as mock_acs:

            crowd_result = replace(base_score, total_score=78.0, explanation="Selected because it is highly popular; Crowd baseline: expected crowd pressure is moderate.")
            mock_acs.return_value = crowd_result

            result = _apply_weather_and_crowd(base_score, destination, trip, None)

            # Weather should not be applied
            mock_aws.assert_not_called()

            # Crowd should still be applied
            mock_acs.assert_called_once()

            assert result == crowd_result


class TestRankCandidatesWithIntelligence:
    """Tests for the _rank_candidates_with_intelligence function."""

    def test_rank_candidates_basic(self):
        """Test basic ranking with intelligence."""
        destinations = [
            make_mock_destination(1, "Dest 1", 80.0),
            make_mock_destination(2, "Dest 2", 70.0),
        ]
        trip = make_mock_trip()

        # Mock the database session
        mock_db = MagicMock()

        with patch('app.services.itinerary_generator.rank_destinations') as mock_rd, \
             patch('app.services.itinerary_generator.get_destination_weather_context') as mock_wc, \
             patch('app.services.itinerary_generator._apply_personalization') as mock_ap, \
             patch('app.services.itinerary_generator._apply_weather_and_crowd') as mock_awc:

            # Mock the rank_destinations to return scored destinations
            scored_dests = [
                DestinationScore(
                    destination=destinations[0],
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Test explanation 1",
                ),
                DestinationScore(
                    destination=destinations[1],
                    total_score=75.0,
                    preference_score=60.0,
                    popularity_score=70.0,
                    budget_score=80.0,
                    duration_score=75.0,
                    accessibility_score=90.0,
                    explanation="Test explanation 2",
                ),
            ]
            mock_rd.return_value = scored_dests

            # Mock weather contexts
            mock_wc.side_effect = [None, None]  # No weather context for both

            # Mock personalization and weather/crowd to return the same scores
            mock_ap.side_effect = lambda s, d, t, p: s
            mock_awc.side_effect = lambda s, d, t, wc: s

            result = _rank_candidates_with_intelligence(
                mock_db, trip, destinations, None
            )

            # Should return ranked destinations
            assert len(result) == 2
            assert result[0].destination.id == 1  # Higher score first
            assert result[1].destination.id == 2

    def test_rank_candidates_with_personalization(self):
        """Test ranking with personalization profile."""
        destinations = [
            make_mock_destination(1, "Dest 1", 80.0),
            make_mock_destination(2, "Dest 2", 70.0),
        ]
        trip = make_mock_trip()
        profile = make_mock_personalization_profile()

        mock_db = MagicMock()

        with patch('app.services.itinerary_generator.rank_destinations') as mock_rd, \
             patch('app.services.itinerary_generator.get_destination_weather_context') as mock_wc, \
             patch('app.services.itinerary_generator._apply_personalization') as mock_ap, \
             patch('app.services.itinerary_generator._apply_weather_and_crowd') as mock_awc:

            scored_dests = [
                DestinationScore(
                    destination=destinations[0],
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Test explanation 1",
                ),
                DestinationScore(
                    destination=destinations[1],
                    total_score=75.0,
                    preference_score=60.0,
                    popularity_score=70.0,
                    budget_score=80.0,
                    duration_score=75.0,
                    accessibility_score=90.0,
                    explanation="Test explanation 2",
                ),
            ]
            mock_rd.return_value = scored_dests
            mock_wc.side_effect = [None, None]
            mock_ap.side_effect = lambda s, d, t, p: replace(s, total_score=s.total_score + 5.0)
            mock_awc.side_effect = lambda s, d, t, wc: s

            result = _rank_candidates_with_intelligence(
                mock_db, trip, destinations, profile
            )

            # Personalization should have been applied
            mock_ap.assert_called()

            # Should still return ranked destinations
            assert len(result) == 2

    def test_rank_candidates_weather_crowd_without_personalization(self):
        """Test that weather and crowd are applied even without personalization."""
        destinations = [
            make_mock_destination(1, "Dest 1", 80.0),
        ]
        trip = make_mock_trip()

        mock_db = MagicMock()

        with patch('app.services.itinerary_generator.rank_destinations') as mock_rd, \
             patch('app.services.itinerary_generator.get_destination_weather_context') as mock_wc, \
             patch('app.services.itinerary_generator._apply_personalization') as mock_ap, \
             patch('app.services.itinerary_generator._apply_weather_and_crowd') as mock_awc:

            scored_dests = [
                DestinationScore(
                    destination=destinations[0],
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Test explanation",
                ),
            ]
            mock_rd.return_value = scored_dests
            mock_wc.return_value = None  # No weather context

            # Mock to return modified score to show it was called
            mock_awc.return_value = replace(scored_dests[0], total_score=80.0)

            result = _rank_candidates_with_intelligence(
                mock_db, trip, destinations, None  # No personalization profile
            )

            # Personalization should NOT have been applied
            mock_ap.assert_not_called()

            # Weather and crowd should have been applied
            mock_awc.assert_called_once()

            # Should return the modified score
            assert result[0].total_score == 80.0


class TestBuildGenerationPipeline:
    """Tests for the _build_generation_pipeline function."""

    def test_build_pipeline_basic(self):
        """Test basic pipeline building."""
        destinations = [
            make_mock_destination(1, "Dest 1", 80.0),
            make_mock_destination(2, "Dest 2", 70.0),
        ]
        trip = make_mock_trip()

        mock_db = MagicMock()
        start_coordinates = (13.0500, 80.2824)  # Bangalore coordinates

        with patch('app.services.itinerary_generator._rank_candidates_with_intelligence') as mock_rcwi, \
             patch('app.services.itinerary_generator.get_coordinates') as mock_gc, \
             patch('app.services.itinerary_generator.geocode_location') as mock_gl:

            # Mock the ranking function
            scored_dests = [
                DestinationScore(
                    destination=destinations[0],
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Test explanation 1",
                ),
                DestinationScore(
                    destination=destinations[1],
                    total_score=75.0,
                    preference_score=60.0,
                    popularity_score=70.0,
                    budget_score=80.0,
                    duration_score=75.0,
                    accessibility_score=90.0,
                    explanation="Test explanation 2",
                ),
            ]
            mock_rcwi.return_value = scored_dests

            # Mock coordinates
            mock_gc.side_effect = [(13.0500, 80.2824), (13.0510, 80.2830)]
            mock_gl.return_value = start_coordinates

            result = _build_generation_pipeline(
                mock_db, trip, destinations, None, start_coordinates
            )

            ranked_candidates, coordinates = result

            # Should return the ranked candidates
            assert len(ranked_candidates) == 2

            # Should return coordinates including start
            assert len(coordinates) == 3  # Start + 2 destinations
            assert coordinates[0] == start_coordinates

    def test_build_pipeline_no_candidates(self):
        """Test pipeline with no candidates raises error."""
        trip = make_mock_trip()
        mock_db = MagicMock()

        with patch('app.services.itinerary_generator._rank_candidates_with_intelligence') as mock_rcwi:
            mock_rcwi.return_value = []  # No ranked candidates

            with pytest.raises(ItineraryGenerationError, match="No destinations are available"):
                _build_generation_pipeline(mock_db, trip, [], None)

    def test_build_pipeline_too_many_coordinates(self):
        """Test pipeline with too many coordinates raises error."""
        # The pipeline limits to MAX_MAPBOX_DESTINATIONS (24) candidates, so we need to
        # mock the ranking function to return more than 24 to test the coordinate limit
        destinations = [make_mock_destination(i, f"Dest {i}", 70.0) for i in range(1, 30)]
        trip = make_mock_trip()

        mock_db = MagicMock()
        start_coordinates = (13.0500, 80.2824)

        with patch('app.services.itinerary_generator._rank_candidates_with_intelligence') as mock_rcwi, \
             patch('app.services.itinerary_generator.get_coordinates') as mock_gc, \
             patch('app.services.itinerary_generator.geocode_location') as mock_gl:

            # Mock 26 destinations to be returned (which would exceed 25 total coordinates)
            scored_dests = [
                DestinationScore(
                    destination=dest,
                    total_score=70.0 + i,
                    preference_score=70.0,
                    popularity_score=70.0,
                    budget_score=70.0,
                    duration_score=70.0,
                    accessibility_score=70.0,
                    explanation="Test",
                ) for i, dest in enumerate(destinations[:26])  # 26 destinations
            ]
            mock_rcwi.return_value = scored_dests

            # Mock coordinates for all destinations
            mock_gc.side_effect = [(13.0500 + i * 0.0001, 80.2824 + i * 0.0001) for i in range(26)]
            mock_gl.return_value = start_coordinates

            result = _build_generation_pipeline(mock_db, trip, destinations[:26], None, start_coordinates)

            ranked_candidates, coordinates = result

            # Should be limited to MAX_MAPBOX_DESTINATIONS (24)
            assert len(ranked_candidates) == 24

            # Should have 25 coordinates total (24 destinations + 1 start)
            assert len(coordinates) == 25


class TestConstants:
    """Test that constants are properly defined."""

    def test_default_visit_duration(self):
        """Test that default visit duration is set."""
        assert DEFAULT_VISIT_DURATION_MINUTES == 60

    def test_max_mapbox_destinations(self):
        """Test that Mapbox destination limit is set."""
        assert MAX_MAPBOX_DESTINATIONS == 24


class TestExecuteItineraryPlanning:
    """Tests for the _execute_itinerary_planning function."""

    def test_execute_planning_basic(self):
        """Test basic execution of the shared planning pipeline."""
        # Create mock destinations
        destinations = [
            make_mock_destination(1, "Dest 1", 80.0, 100.0, 60),
            make_mock_destination(2, "Dest 2", 70.0, 50.0, 45),
        ]

        # Create mock destination scores
        ranked_candidates = [
            DestinationScore(
                destination=destinations[0],
                total_score=85.0,
                preference_score=70.0,
                popularity_score=80.0,
                budget_score=90.0,
                duration_score=85.0,
                accessibility_score=100.0,
                explanation="Selected because it is highly popular.",
            ),
            DestinationScore(
                destination=destinations[1],
                total_score=75.0,
                preference_score=60.0,
                popularity_score=70.0,
                budget_score=80.0,
                duration_score=75.0,
                accessibility_score=90.0,
                explanation="Selected because it fits the selected budget.",
            ),
        ]

        trip = make_mock_trip(available_duration_minutes=480)
        start_coordinates = (13.0500, 80.2824)
        candidate_coordinates = [start_coordinates, (13.0510, 80.2830), (13.0520, 80.2840)]

        with patch('app.services.itinerary_generator.get_matrix') as mock_matrix, \
             patch('app.services.itinerary_generator.optimize_itinerary') as mock_optimize, \
             patch('app.services.itinerary_generator.get_directions') as mock_directions, \
             patch('app.services.itinerary_generator.get_coordinates') as mock_coords:

            # Mock Mapbox matrix to return empty travel matrix
            mock_matrix.return_value = ([[0, 10, 20], [10, 0, 5], [20, 5, 0]], [])

            # Mock optimization result with one selected destination
            from app.services.itinerary_optimizer import OptimizationResult, OptimizedStop
            mock_optimize.return_value = OptimizationResult(
                stops=[
                    OptimizedStop(
                        destination_score=ranked_candidates[0],
                        sequence=1,
                        travel_minutes_from_previous=10,
                        visit_minutes=60,
                        entry_fee=100.0,
                    )
                ],
                total_travel_minutes=10,
                total_visit_minutes=60,
                total_duration_minutes=70,
                total_cost=100.0,
            )

            # Mock directions to return valid route legs
            mock_directions.return_value = [
                {"distance_km": 5.0, "duration_minutes": 10.0}
            ]

            # Mock coordinates for destinations
            mock_coords.side_effect = [
                (13.0510, 80.2830),  # For the selected destination
            ]

            # Execute the planning
            selected, total_duration, total_travel_duration, total_cost = _execute_itinerary_planning(
                ranked_candidates=ranked_candidates,
                candidate_coordinates=candidate_coordinates,
                trip=trip,
                start_coordinates=start_coordinates,
            )

            # Verify results
            assert len(selected) == 1
            assert selected[0][0].id == 1  # First destination selected
            assert total_duration > 0
            assert total_travel_duration >= 0
            assert total_cost > 0

    def test_execute_planning_mapbox_matrix_error(self):
        """Test that Mapbox matrix errors are properly handled."""
        destinations = [make_mock_destination(1, "Dest 1", 80.0)]
        ranked_candidates = [
            DestinationScore(
                destination=destinations[0],
                total_score=85.0,
                preference_score=70.0,
                popularity_score=80.0,
                budget_score=90.0,
                duration_score=85.0,
                accessibility_score=100.0,
                explanation="Test",
            ),
        ]

        trip = make_mock_trip()
        start_coordinates = (13.0500, 80.2824)
        candidate_coordinates = [start_coordinates, (13.0510, 80.2830)]

        with patch('app.services.itinerary_generator.get_matrix') as mock_matrix:
            mock_matrix.side_effect = MapboxServiceError("Matrix error")

            with pytest.raises(ItineraryGenerationError, match="Unable to calculate travel times"):
                _execute_itinerary_planning(
                    ranked_candidates=ranked_candidates,
                    candidate_coordinates=candidate_coordinates,
                    trip=trip,
                    start_coordinates=start_coordinates,
                )

    def test_execute_planning_no_stops(self):
        """Test that empty optimization results are handled."""
        destinations = [make_mock_destination(1, "Dest 1", 80.0, 1000.0)]  # Expensive destination
        ranked_candidates = [
            DestinationScore(
                destination=destinations[0],
                total_score=85.0,
                preference_score=70.0,
                popularity_score=80.0,
                budget_score=90.0,
                duration_score=85.0,
                accessibility_score=100.0,
                explanation="Test",
            ),
        ]

        # Trip with very low budget
        trip = make_mock_trip(budget_amount=50.0)
        start_coordinates = (13.0500, 80.2824)
        candidate_coordinates = [start_coordinates, (13.0510, 80.2830)]

        with patch('app.services.itinerary_generator.get_matrix') as mock_matrix, \
             patch('app.services.itinerary_generator.optimize_itinerary') as mock_optimize:

            mock_matrix.return_value = ([[0, 10], [10, 0]], [])

            # Mock empty optimization result (no destinations fit constraints)
            from app.services.itinerary_optimizer import OptimizationResult
            mock_optimize.return_value = OptimizationResult(
                stops=[],
                total_travel_minutes=0,
                total_visit_minutes=0,
                total_duration_minutes=0,
                total_cost=0.0,
            )

            with pytest.raises(ItineraryGenerationError, match="No destinations fit"):
                _execute_itinerary_planning(
                    ranked_candidates=ranked_candidates,
                    candidate_coordinates=candidate_coordinates,
                    trip=trip,
                    start_coordinates=start_coordinates,
                )

    def test_execute_planning_directions_verification_error(self):
        """Test that Mapbox Directions errors are properly handled."""
        destinations = [make_mock_destination(1, "Dest 1", 80.0)]
        ranked_candidates = [
            DestinationScore(
                destination=destinations[0],
                total_score=85.0,
                preference_score=70.0,
                popularity_score=80.0,
                budget_score=90.0,
                duration_score=85.0,
                accessibility_score=100.0,
                explanation="Test",
            ),
        ]

        trip = make_mock_trip()
        start_coordinates = (13.0500, 80.2824)
        candidate_coordinates = [start_coordinates, (13.0510, 80.2830)]

        with patch('app.services.itinerary_generator.get_matrix') as mock_matrix, \
             patch('app.services.itinerary_generator.optimize_itinerary') as mock_optimize, \
             patch('app.services.itinerary_generator.get_directions') as mock_directions, \
             patch('app.services.itinerary_generator.get_coordinates') as mock_coords:

            mock_matrix.return_value = ([[0, 10], [10, 0]], [])

            from app.services.itinerary_optimizer import OptimizationResult, OptimizedStop
            mock_optimize.return_value = OptimizationResult(
                stops=[
                    OptimizedStop(
                        destination_score=ranked_candidates[0],
                        sequence=1,
                        travel_minutes_from_previous=10,
                        visit_minutes=60,
                        entry_fee=100.0,
                    )
                ],
                total_travel_minutes=10,
                total_visit_minutes=60,
                total_duration_minutes=70,
                total_cost=100.0,
            )

            mock_directions.side_effect = MapboxServiceError("Directions error")
            mock_coords.return_value = (13.0510, 80.2830)

            with pytest.raises(ItineraryGenerationError, match="Unable to verify the optimized route"):
                _execute_itinerary_planning(
                    ranked_candidates=ranked_candidates,
                    candidate_coordinates=candidate_coordinates,
                    trip=trip,
                    start_coordinates=start_coordinates,
                )

    def test_execute_planning_budget_exceeded(self):
        """Test that budget constraint violations are properly handled."""
        destinations = [
            make_mock_destination(1, "Expensive Dest", 80.0, 1000.0),  # Very expensive
            make_mock_destination(2, "Cheap Dest", 70.0, 50.0),       # Affordable
        ]
        ranked_candidates = [
            DestinationScore(
                destination=destinations[0],
                total_score=85.0,
                preference_score=70.0,
                popularity_score=80.0,
                budget_score=90.0,
                duration_score=85.0,
                accessibility_score=100.0,
                explanation="Test",
            ),
            DestinationScore(
                destination=destinations[1],
                total_score=75.0,
                preference_score=60.0,
                popularity_score=70.0,
                budget_score=80.0,
                duration_score=75.0,
                accessibility_score=90.0,
                explanation="Test",
            ),
        ]

        # Trip with budget that can't handle the expensive destination
        trip = make_mock_trip(budget_amount=200.0)
        start_coordinates = (13.0500, 80.2824)
        candidate_coordinates = [start_coordinates, (13.0510, 80.2830), (13.0520, 80.2840)]

        with patch('app.services.itinerary_generator.get_matrix') as mock_matrix, \
             patch('app.services.itinerary_generator.optimize_itinerary') as mock_optimize, \
             patch('app.services.itinerary_generator.get_directions') as mock_directions, \
             patch('app.services.itinerary_generator.get_coordinates') as mock_coords:

            mock_matrix.return_value = ([[0, 10, 20], [10, 0, 5], [20, 5, 0]], [])

            from app.services.itinerary_optimizer import OptimizationResult, OptimizedStop
            # Optimizer selects both destinations (may not be realistic but for testing)
            mock_optimize.return_value = OptimizationResult(
                stops=[
                    OptimizedStop(
                        destination_score=ranked_candidates[0],
                        sequence=1,
                        travel_minutes_from_previous=10,
                        visit_minutes=60,
                        entry_fee=1000.0,
                    ),
                    OptimizedStop(
                        destination_score=ranked_candidates[1],
                        sequence=2,
                        travel_minutes_from_previous=5,
                        visit_minutes=45,
                        entry_fee=50.0,
                    ),
                ],
                total_travel_minutes=15,
                total_visit_minutes=105,
                total_duration_minutes=120,
                total_cost=1050.0,
            )

            # Mock directions to return valid legs that match the selected destinations
            mock_directions.return_value = [
                {"distance_km": 5.0, "duration_minutes": 10.0},  # To first destination
                {"distance_km": 2.0, "duration_minutes": 5.0},   # To second destination
            ]

            # Mock coordinates for destinations
            mock_coords.side_effect = [
                (13.0510, 80.2830),  # First destination
                (13.0520, 80.2840),  # Second destination
            ]

            with pytest.raises(ItineraryGenerationError, match="exceeds the trip budget"):
                _execute_itinerary_planning(
                    ranked_candidates=ranked_candidates,
                    candidate_coordinates=candidate_coordinates,
                    trip=trip,
                    start_coordinates=start_coordinates,
                )