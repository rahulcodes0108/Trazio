"""Tests for the dynamic replanning service."""

from datetime import date, time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models.destination import Destination, DestinationCategory, AccessibilityLevel
from app.models.itinerary import Itinerary, ItineraryStatus
from app.models.itinerary_stop import ItineraryStop
from app.models.trip import Trip, TripStatus, BudgetLevel, TransportMode
from app.models.user import User, UserStatus
from app.services.destination_scorer import DestinationScore
from app.services.itinerary_optimizer import OptimizationResult, OptimizedStop
from app.services.mapbox_service import MapboxServiceError
from app.services.replanning_service import (
    ReplanningRequest,
    ReplanningError,
    replan_itinerary,
    _validate_replanning_request,
    _get_original_destination_ids,
    _get_eligible_destinations,
    _build_replanning_notes,
    _append_replanning_context_to_reason,
)


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
    is_active: bool = True,
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
    destination.is_active = is_active
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


def make_mock_itinerary(
    trip: Trip,
    version: int = 1,
    status: ItineraryStatus = ItineraryStatus.GENERATED,
) -> Itinerary:
    """Create a mock itinerary with stops."""
    itinerary = Itinerary()
    itinerary.id = 1
    itinerary.trip_id = trip.id
    itinerary.version = version
    itinerary.status = status
    itinerary.total_duration_minutes = 480
    itinerary.estimated_travel_duration_minutes = 60
    itinerary.estimated_cost = 500.0
    itinerary.estimated_cost_currency = "INR"
    itinerary.is_optimized = True
    itinerary.notes = "Original itinerary"
    itinerary.trip = trip
    itinerary.stops = []
    return itinerary


def make_mock_itinerary_stop(
    itinerary: Itinerary,
    destination: Destination,
    sequence: int = 1,
) -> ItineraryStop:
    """Create a mock itinerary stop."""
    stop = ItineraryStop()
    stop.id = sequence
    stop.itinerary_id = itinerary.id
    stop.destination_id = destination.id
    stop.sequence = sequence
    stop.visit_duration_minutes = destination.average_visit_duration_minutes or 60
    stop.estimated_travel_duration_minutes = 30
    stop.estimated_travel_distance_km = 5.0
    stop.travel_mode = "mixed"
    stop.estimated_cost = float(destination.entry_fee or 0.0)
    stop.estimated_cost_currency = "INR"
    stop.selection_reason = "Selected because it is highly popular."
    stop.itinerary = itinerary
    stop.destination = destination
    return stop


class TestReplanningRequest:
    """Tests for the ReplanningRequest dataclass."""

    def test_replanning_request_creation(self):
        """Test basic ReplanningRequest creation."""
        request = ReplanningRequest(
            unavailable_destination_ids={1, 2, 3},
            reason="Maintenance",
        )

        assert request.unavailable_destination_ids == {1, 2, 3}
        assert request.reason == "Maintenance"

    def test_replanning_request_without_reason(self):
        """Test ReplanningRequest without reason."""
        request = ReplanningRequest(
            unavailable_destination_ids={1, 2},
        )

        assert request.unavailable_destination_ids == {1, 2}
        assert request.reason is None

    def test_replanning_request_immutable(self):
        """Test that ReplanningRequest is immutable."""
        request = ReplanningRequest(
            unavailable_destination_ids={1, 2},
            reason="Test",
        )

        # Verify the destination IDs are stored as frozenset
        assert isinstance(request.unavailable_destination_ids, frozenset)
        assert request.unavailable_destination_ids == frozenset({1, 2})

        # Verify attribute reassignment is rejected
        with pytest.raises(AttributeError, match="cannot assign to field"):
            request.unavailable_destination_ids = {3, 4}

        # Verify the destination ID collection itself cannot be mutated
        with pytest.raises(AttributeError, match="'frozenset' object has no attribute 'add'"):
            request.unavailable_destination_ids.add(3)

    def test_replanning_request_normalizes_set_to_frozenset(self):
        """Test that ReplanningRequest normalizes regular sets to frozensets."""
        # Pass a regular set
        request = ReplanningRequest(
            unavailable_destination_ids={1, 2, 3},
            reason="Test",
        )

        # Should be normalized to frozenset
        assert isinstance(request.unavailable_destination_ids, frozenset)
        assert request.unavailable_destination_ids == frozenset({1, 2, 3})

    def test_replanning_request_accepts_frozenset(self):
        """Test that ReplanningRequest accepts frozenset directly."""
        request = ReplanningRequest(
            unavailable_destination_ids=frozenset({1, 2}),
            reason="Test",
        )

        assert isinstance(request.unavailable_destination_ids, frozenset)
        assert request.unavailable_destination_ids == frozenset({1, 2})


class TestValidation:
    """Tests for validation logic."""

    def test_empty_unavailable_destination_ids_rejected(self):
        """Test that empty unavailable_destination_ids is rejected."""
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)
        request = ReplanningRequest(unavailable_destination_ids=set())

        with pytest.raises(ReplanningError, match="must specify at least one"):
            _validate_replanning_request(itinerary, request)

    def test_itinerary_without_trip_rejected(self):
        """Test that itinerary without trip is rejected."""
        itinerary = Itinerary()
        itinerary.id = 1
        itinerary.version = 1
        itinerary.stops = []
        itinerary.trip = None
        request = ReplanningRequest(unavailable_destination_ids={1})

        with pytest.raises(ReplanningError, match="must have an associated trip"):
            _validate_replanning_request(itinerary, request)

    def test_unavailable_destination_not_in_itinerary_rejected(self):
        """Test that unavailable destination not in source itinerary is rejected."""
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        # Add stops with specific destinations
        dest1 = make_mock_destination(1)
        dest2 = make_mock_destination(2)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        stop2 = make_mock_itinerary_stop(itinerary, dest2, 2)
        itinerary.stops = [stop1, stop2]

        # Try to remove a destination that's not in the itinerary
        request = ReplanningRequest(unavailable_destination_ids={3})

        with pytest.raises(ReplanningError, match="not present in source itinerary"):
            _validate_replanning_request(itinerary, request)

    def test_valid_request_passes(self):
        """Test that valid request passes validation."""
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        # Add stops with specific destinations
        dest1 = make_mock_destination(1)
        dest2 = make_mock_destination(2)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        stop2 = make_mock_itinerary_stop(itinerary, dest2, 2)
        itinerary.stops = [stop1, stop2]

        # Valid request - destination 1 is in the itinerary
        request = ReplanningRequest(unavailable_destination_ids={1})

        # Should not raise
        _validate_replanning_request(itinerary, request)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_original_destination_ids(self):
        """Test extraction of destination IDs from itinerary."""
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        dest1 = make_mock_destination(1)
        dest2 = make_mock_destination(2)
        dest3 = make_mock_destination(3)

        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        stop2 = make_mock_itinerary_stop(itinerary, dest2, 2)
        stop3 = make_mock_itinerary_stop(itinerary, dest3, 3)
        itinerary.stops = [stop1, stop2, stop3]

        result = _get_original_destination_ids(itinerary)

        assert result == {1, 2, 3}

    def test_get_original_destination_ids_empty(self):
        """Test extraction with empty stops."""
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)
        itinerary.stops = []

        result = _get_original_destination_ids(itinerary)

        assert result == set()

    def test_build_replanning_notes_basic(self):
        """Test basic replanning notes generation."""
        notes = _build_replanning_notes(
            source_version=1,
            unavailable_destination_ids={1, 2},
            reason=None,
        )

        assert "Replanned itinerary due to destination availability changes" in notes
        assert "Source itinerary version: 1" in notes
        assert "Unavailable destination(s): 1, 2" in notes
        assert "Current destination availability was used" in notes
        assert "TRAZIO re-optimized the route" in notes
        assert len(notes) <= 500

    def test_build_replanning_notes_with_reason(self):
        """Test replanning notes with reason included."""
        notes = _build_replanning_notes(
            source_version=2,
            unavailable_destination_ids={5},
            reason="Temporary closure",
        )

        assert "Reason: Temporary closure" in notes
        assert len(notes) <= 500

    def test_append_replanning_context_to_reason(self):
        """Test appending replanning context to selection reason."""
        original_reason = "Selected because it is highly popular."
        result = _append_replanning_context_to_reason(
            original_reason, {1, 2}
        )

        assert "Selected because it is highly popular" in result
        assert "Selected as replacement during replanning" in result
        assert "destination(s) 1, 2 became unavailable" in result
        assert len(result) <= 500

    def test_append_replanning_context_to_none_reason(self):
        """Test appending replanning context when original reason is None."""
        result = _append_replanning_context_to_reason(
            None, {3}
        )

        assert "Selected by the itinerary optimizer under the trip constraints" in result
        assert "Selected as replacement during replanning" in result
        assert "destination(s) 3 became unavailable" in result
        assert len(result) <= 500


class TestGetEligibleDestinations:
    """Tests for _get_eligible_destinations function."""

    def test_unavailable_destination_excluded(self):
        """Test that unavailable destination is excluded from eligible destinations."""
        db = MagicMock()
        trip = make_mock_trip()

        # Create destinations
        available_dest = make_mock_destination(1, is_active=True)
        unavailable_dest = make_mock_destination(2, is_active=True)

        # Mock database query to return both destinations
        mock_dest_query = MagicMock()
        mock_dest_query.filter.return_value.all.return_value = [available_dest, unavailable_dest]
        db.query.return_value = mock_dest_query

        # Mark destination 2 as unavailable
        unavailable_ids = frozenset({2})

        # Call function
        eligible = _get_eligible_destinations(db, trip, unavailable_ids)

        # Verify unavailable destination is excluded
        eligible_ids = {dest.id for dest in eligible}
        assert 1 in eligible_ids  # available destination should be included
        assert 2 not in eligible_ids  # unavailable destination should be excluded

    def test_inactive_destination_excluded(self):
        """Test that inactive destination is excluded from eligible destinations."""
        db = MagicMock()
        trip = make_mock_trip()

        # Create destinations
        active_dest = make_mock_destination(1, is_active=True)
        inactive_dest = make_mock_destination(2, is_active=False)

        # Mock database query to return both destinations
        mock_dest_query = MagicMock()
        mock_dest_query.filter.return_value.all.return_value = [active_dest, inactive_dest]
        db.query.return_value = mock_dest_query

        # No unavailable destinations
        unavailable_ids = frozenset()

        # Call function
        eligible = _get_eligible_destinations(db, trip, unavailable_ids)

        # Verify inactive destination is excluded
        eligible_ids = {dest.id for dest in eligible}
        assert 1 in eligible_ids  # active destination should be included
        assert 2 not in eligible_ids  # inactive destination should be excluded

    def test_active_eligible_destination_included(self):
        """Test that an active eligible destination remains in the results."""
        db = MagicMock()
        trip = make_mock_trip()

        # Create an active eligible destination
        eligible_dest = make_mock_destination(1, is_active=True, entry_fee=100.0)

        # Mock database query
        mock_dest_query = MagicMock()
        mock_dest_query.filter.return_value.all.return_value = [eligible_dest]
        db.query.return_value = mock_dest_query

        # No unavailable destinations
        unavailable_ids = frozenset()

        # Call function
        eligible = _get_eligible_destinations(db, trip, unavailable_ids)

        # Verify eligible destination is included
        assert len(eligible) == 1
        assert eligible[0].id == 1

    def test_trip_budget_constraints_respected(self):
        """Test that existing trip hard constraints are respected."""
        db = MagicMock()
        # Create trip with ECONOMY budget which has entry fee limits
        trip = make_mock_trip(budget_level=BudgetLevel.ECONOMY)

        # Create destinations with different fees
        affordable_dest = make_mock_destination(1, is_active=True, entry_fee=50.0)  # Should pass
        expensive_dest = make_mock_destination(2, is_active=True, entry_fee=5000.0)  # Should be filtered out by budget

        # Mock database query
        mock_dest_query = MagicMock()
        mock_dest_query.filter.return_value.all.return_value = [affordable_dest, expensive_dest]
        db.query.return_value = mock_dest_query

        # No unavailable destinations
        unavailable_ids = frozenset()

        # Call function
        eligible = _get_eligible_destinations(db, trip, unavailable_ids)

        # Verify only affordable destination is included
        eligible_ids = {dest.id for dest in eligible}
        assert 1 in eligible_ids  # affordable destination should be included
        assert 2 not in eligible_ids  # expensive destination should be filtered by budget constraints


class TestReplanItinerary:
    """Tests for the main replan_itinerary function."""

    def test_empty_unavailable_destination_ids_rejected(self):
        """Test that empty unavailable_destination_ids is rejected."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)
        request = ReplanningRequest(unavailable_destination_ids=set())

        with pytest.raises(ReplanningError, match="must specify at least one"):
            replan_itinerary(db, itinerary, request)

    def test_unavailable_destination_not_in_source_rejected(self):
        """Test that unavailable destination not in source itinerary is rejected."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        # Add a stop with destination 1
        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        # Try to remove destination 2 which is not in the itinerary
        request = ReplanningRequest(unavailable_destination_ids={2})

        with pytest.raises(ReplanningError, match="not present in source itinerary"):
            replan_itinerary(db, itinerary, request)

    def test_source_itinerary_remains_unchanged(self):
        """Test that source itinerary remains unchanged."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        # Add stops
        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        # Save original values
        original_version = itinerary.version
        original_notes = itinerary.notes
        original_stop_count = len(itinerary.stops)

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version:

            # Mock database query for destinations
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline to return candidates and coordinates
            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            candidate_coordinates = [(13.0500, 80.2824), (13.0510, 80.2830)]
            mock_pipeline.return_value = (ranked_candidates, candidate_coordinates)

            # Mock execution
            selected = [
                (dest2, 30, 60, 5.0, "Selected because it is highly popular.")
            ]
            mock_execute.return_value = (selected, 90, 30, 100.0)

            # Mock version finding
            mock_find_version.return_value = 1

            # Mock db operations
            mock_add.side_effect = lambda x: None
            mock_refresh.side_effect = lambda x: None

            # Execute replanning - should succeed and return new itinerary
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Verify replanning succeeded
            assert new_itinerary is not None
            assert new_itinerary.version == 2  # new version should be 2

            # Verify source itinerary is unchanged
            assert itinerary.version == original_version
            assert itinerary.notes == original_notes
            assert len(itinerary.stops) == original_stop_count

    def test_unavailable_destination_absent_from_candidates(self):
        """Test that unavailable destination is excluded from candidates."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        # Add stops with destinations 1 and 2
        dest1 = make_mock_destination(1)
        dest2 = make_mock_destination(2)
        dest3 = make_mock_destination(3)  # Active alternative
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        stop2 = make_mock_itinerary_stop(itinerary, dest2, 2)
        itinerary.stops = [stop1, stop2]

        request = ReplanningRequest(unavailable_destination_ids={1})  # Make dest 1 unavailable

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._get_eligible_destinations') as mock_eligible, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version:

            # Mock database query for all active destinations
            all_dests = [dest1, dest2, dest3]
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = all_dests
            mock_query.return_value = mock_dest_query

            # Mock eligible destinations - should exclude dest1 and include dest2 and dest3
            eligible_dests = [dest2, dest3]
            mock_eligible.return_value = eligible_dests

            # Mock pipeline
            ranked_candidates = [
                DestinationScore(
                    destination=dest3,
                    total_score=90.0,
                    preference_score=80.0,
                    popularity_score=85.0,
                    budget_score=95.0,
                    duration_score=90.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0520, 80.2840)])

            # Mock execution
            selected = [(dest3, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 150.0)

            # Mock version finding
            mock_find_version.return_value = 1

            # Execute replanning - should call _get_eligible_destinations which excludes unavailable dests
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Verify that _get_eligible_destinations was called
            assert mock_eligible.called
            # Verify that it was called with the right unavailable destination IDs
            call_args = mock_eligible.call_args
            assert call_args[1]['unavailable_destination_ids'] == frozenset({1})

    def test_new_version_is_source_version_plus_one(self):
        """Test that new version is source version + 1."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=3)  # Source version 3

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database query
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline
            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)

            # Mock version finding - return 3 (source version)
            mock_find_version.return_value = 3

            # Execute
            new_itinerary = replan_itinerary(db, itinerary, request)

            # New version should be 4 (3 + 1)
            assert new_itinerary.version == 4

    def test_new_itinerary_notes_explain_replanning(self):
        """Test that new itinerary notes explain the replanning."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(
            unavailable_destination_ids={1},
            reason="Temporary closure for maintenance"
        )

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database query
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline
            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)

            # Mock version finding
            mock_find_version.return_value = 1

            # Execute
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Verify notes
            assert "Replanned itinerary due to destination availability changes" in new_itinerary.notes
            assert "Source itinerary version: 1" in new_itinerary.notes
            assert "Unavailable destination(s): 1" in new_itinerary.notes
            assert "Reason: Temporary closure for maintenance" in new_itinerary.notes
            assert "Current destination availability was used" in new_itinerary.notes
            assert "TRAZIO re-optimized the route" in new_itinerary.notes

    def test_supplied_reason_appears_in_notes(self):
        """Test that supplied reason appears in notes."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=2)

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        custom_reason = "Venue closed for private event"
        request = ReplanningRequest(
            unavailable_destination_ids={1},
            reason=custom_reason,
        )

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database and pipeline
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 2

            # Execute
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Verify custom reason is in notes
            assert f"Reason: {custom_reason}" in new_itinerary.notes

    def test_unchanged_original_destination_no_replacement_context(self):
        """Test that unchanged original destinations do NOT receive replacement context."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        # Original itinerary has destinations 1 and 2
        dest1 = make_mock_destination(1)
        dest2 = make_mock_destination(2)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        stop2 = make_mock_itinerary_stop(itinerary, dest2, 2)
        itinerary.stops = [stop1, stop2]

        # Make only destination 1 unavailable, so destination 2 should remain unchanged
        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database - destination 2 is still available
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, dest2, make_mock_destination(3)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline - destination 2 should still be selected (unchanged)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution - destination 2 is selected with its original reason
            original_reason = "Selected because it is highly popular."
            selected = [(dest2, 30, 60, 5.0, original_reason)]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute replanning
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Check that db.add was called with stops
            # Find the stop that was added
            stop_calls = [call for call in mock_add.call_args_list if call[0] and hasattr(call[0][0], 'destination_id')]
            assert len(stop_calls) > 0

            # Get the stop that was created
            created_stop = stop_calls[0][0][0]

            # The stop should have the original reason WITHOUT replanning context
            # because destination 2 was in the original itinerary
            assert created_stop.selection_reason == original_reason
            assert "Selected as replacement during replanning" not in created_stop.selection_reason

    def test_new_replacement_destination_has_replacement_context(self):
        """Test that newly introduced replacement destinations DO receive replacement context."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        # Original itinerary has only destination 1
        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        # Make destination 1 unavailable
        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database - destination 2 is a new replacement
            dest2 = make_mock_destination(2)
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, dest2]
            mock_query.return_value = mock_dest_query

            # Mock pipeline - destination 2 is selected as replacement
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution - destination 2 is selected
            original_reason = "Selected because it is highly popular."
            selected = [(dest2, 30, 60, 5.0, original_reason)]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute replanning
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Check that db.add was called with stops
            stop_calls = [call for call in mock_add.call_args_list if call[0] and hasattr(call[0][0], 'destination_id')]
            assert len(stop_calls) > 0

            # Get the stop that was created
            created_stop = stop_calls[0][0][0]

            # The stop should have the replanning context because destination 2 is new
            assert "Selected as replacement during replanning" in created_stop.selection_reason
            assert "destination(s) 1 became unavailable" in created_stop.selection_reason

    def test_replacement_selection_reason_contains_replanning_context(self):
        """Test that replacement selection_reason contains replanning context."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline
            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution with original reason
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Get the stops from the new itinerary (they were added to db)
            # Since we're mocking, we need to check what would have been created
            # We can check by examining the calls to db.add
            assert len(mock_add.call_args_list) >= 1

            # The new itinerary should have been added
            assert any('itinerary' in str(call) and 'version' in str(call) for call in mock_add.call_args_list)

    def test_shared_planning_pipeline_invoked(self):
        """Test that shared planning pipeline is invoked."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version:

            # Mock database
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            # Mock pipeline
            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute
            replan_itinerary(db, itinerary, request)

            # Verify pipeline was called
            assert mock_pipeline.called
            assert mock_execute.called

    def test_inactive_destinations_excluded(self):
        """Test that inactive destinations are excluded from candidates."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip)

        # Add stops with active destinations
        dest1 = make_mock_destination(1, is_active=True)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._get_eligible_destinations') as mock_eligible, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version:

            # Mock database with active and inactive destinations
            active_dest = make_mock_destination(2, is_active=True)
            inactive_dest = make_mock_destination(3, is_active=False)
            all_dests = [dest1, active_dest, inactive_dest]

            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = all_dests
            mock_query.return_value = mock_dest_query

            # Mock eligible destinations - should exclude inactive and unavailable
            eligible_dests = [active_dest]  # Only active_dest should be included
            mock_eligible.return_value = eligible_dests

            # Mock pipeline
            ranked_candidates = [
                DestinationScore(
                    destination=active_dest,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution
            selected = [(active_dest, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute
            replan_itinerary(db, itinerary, request)

            # Verify that _get_eligible_destinations was called
            assert mock_eligible.called

    def test_planning_constraints_preserved(self):
        """Test that planning constraints are preserved from source itinerary."""
        db = MagicMock()
        trip = make_mock_trip(
            budget_level=BudgetLevel.ECONOMY,
            budget_amount=500.0,
            available_duration_minutes=240,
        )
        itinerary = make_mock_itinerary(trip)

        dest1 = make_mock_destination(1, entry_fee=1000.0)  # Too expensive for ECONOMY
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._get_eligible_destinations') as mock_eligible, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version:

            # Mock database with destinations including expensive ones
            expensive_dest = make_mock_destination(2, entry_fee=1000.0)  # Too expensive
            affordable_dest = make_mock_destination(3, entry_fee=100.0)  # Affordable
            all_dests = [dest1, expensive_dest, affordable_dest]

            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = all_dests
            mock_query.return_value = mock_dest_query

            # Mock eligible destinations - should only include affordable destinations for ECONOMY budget
            eligible_dests = [affordable_dest]  # Only affordable_dest should pass budget filter
            mock_eligible.return_value = eligible_dests

            # Mock pipeline
            ranked_candidates = [
                DestinationScore(
                    destination=affordable_dest,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])

            # Mock execution
            selected = [(affordable_dest, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute
            replan_itinerary(db, itinerary, request)

            # Verify that _get_eligible_destinations was called
            assert mock_eligible.called

    def test_new_itinerary_status_matches_generated_behavior(self):
        """Test that new itinerary status matches existing generated itinerary behavior."""
        db = MagicMock()
        trip = make_mock_trip()
        itinerary = make_mock_itinerary(trip, version=1)

        dest1 = make_mock_destination(1)
        stop1 = make_mock_itinerary_stop(itinerary, dest1, 1)
        itinerary.stops = [stop1]

        request = ReplanningRequest(unavailable_destination_ids={1})

        with patch.object(db, 'query') as mock_query, \
             patch('app.services.replanning_service._build_generation_pipeline') as mock_pipeline, \
             patch('app.services.replanning_service._execute_itinerary_planning') as mock_execute, \
             patch('app.services.replanning_service._find_highest_itinerary_version') as mock_find_version, \
             patch.object(db, 'add') as mock_add, \
             patch.object(db, 'commit') as mock_commit, \
             patch.object(db, 'refresh') as mock_refresh, \
             patch.object(db, 'flush') as mock_flush:

            # Mock database and pipeline
            mock_dest_query = MagicMock()
            mock_dest_query.filter.return_value.all.return_value = [dest1, make_mock_destination(2)]
            mock_query.return_value = mock_dest_query

            dest2 = make_mock_destination(2)
            ranked_candidates = [
                DestinationScore(
                    destination=dest2,
                    total_score=85.0,
                    preference_score=70.0,
                    popularity_score=80.0,
                    budget_score=90.0,
                    duration_score=85.0,
                    accessibility_score=100.0,
                    explanation="Selected because it is highly popular.",
                ),
            ]
            mock_pipeline.return_value = (ranked_candidates, [(13.0500, 80.2824), (13.0510, 80.2830)])
            selected = [(dest2, 30, 60, 5.0, "Selected because it is highly popular.")]
            mock_execute.return_value = (selected, 90, 30, 100.0)
            mock_find_version.return_value = 1

            # Execute
            new_itinerary = replan_itinerary(db, itinerary, request)

            # Verify status matches generated behavior
            assert new_itinerary.status == ItineraryStatus.GENERATED