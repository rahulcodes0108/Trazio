"""Tests for itinerary API endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.destination import Destination, DestinationCategory, AccessibilityLevel
from app.models.itinerary import Itinerary, ItineraryStatus
from app.models.itinerary_stop import ItineraryStop
from app.models.trip import Trip, TripStatus, TransportMode, BudgetLevel
from app.models.user import User, UserStatus
from app.repositories.destination_repository import DestinationRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.user_repository import UserRepository
from app.db.session import get_db
from app.main import app

# Test database setup
TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@postgres:5432/trazio_test"
engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    """Create and drop test database tables for each test module."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Provide a transactional database session."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from app.core.security import hash_password
    return UserRepository.create(
        db=db_session,
        email="test@example.com",
        username="testuser",
        hashed_password=hash_password("testpass123"),
        full_name="Test User",
        status=UserStatus.ACTIVE,
        is_verified=False,
    )


@pytest.fixture
def other_user(db_session):
    """Create another test user for ownership tests."""
    from app.core.security import hash_password
    return UserRepository.create(
        db=db_session,
        email="other@example.com",
        username="otheruser",
        hashed_password=hash_password("otherpass123"),
        full_name="Other User",
        status=UserStatus.ACTIVE,
        is_verified=False,
    )


@pytest.fixture
def test_trip(db_session, test_user):
    """Create a test trip."""
    return TripRepository.create(
        db=db_session,
        user_id=test_user.id,
        title="Summer Vacation",
        start_location="New York",
        start_date="2023-07-01",
        end_date="2023-07-10",
        budget_level=BudgetLevel.MID_RANGE,
        transport_mode=TransportMode.MIXED,
        status=TripStatus.PLANNING,
    )


@pytest.fixture
def other_user_trip(db_session, other_user):
    """Create a trip for another user."""
    return TripRepository.create(
        db=db_session,
        user_id=other_user.id,
        title="Other User's Trip",
        start_location="Los Angeles",
        start_date="2023-08-01",
    )


@pytest.fixture
def test_destination(db_session):
    """Create a test destination."""
    return DestinationRepository.create(
        db=db_session,
        name="Eiffel Tower",
        slug="eiffel-tower",
        location_wkt="POINT(2.294481 48.858370)",
        category=DestinationCategory.ATTRACTION,
        description="Iconic Paris landmark",
        city="Paris",
        country="France",
    )


@pytest.fixture
def test_itinerary(db_session, test_trip):
    """Create a test itinerary."""
    return ItineraryRepository.create(
        db=db_session,
        trip_id=test_trip.id,
        version=1,
        status=ItineraryStatus.GENERATED,
        total_duration_minutes=480,
        estimated_travel_duration_minutes=120,
        estimated_cost=500.00,
        estimated_cost_currency="USD",
        notes="Main itinerary",
    )


@pytest.fixture
def other_user_itinerary(db_session, other_user_trip):
    """Create an itinerary for another user's trip."""
    return ItineraryRepository.create(
        db=db_session,
        trip_id=other_user_trip.id,
        version=1,
        status=ItineraryStatus.DRAFT,
    )


@pytest.fixture
def test_itinerary_stop(db_session, test_itinerary, test_destination):
    """Create a test itinerary stop."""
    return ItineraryRepository.create_stop(
        db=db_session,
        itinerary_id=test_itinerary.id,
        destination_id=test_destination.id,
        sequence=1,
        planned_arrival=datetime(2023, 7, 1, 9, 0, 0, tzinfo=timezone.utc),
        planned_departure=datetime(2023, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
        visit_duration_minutes=180,
        estimated_travel_duration_minutes=30,
        estimated_travel_distance_km=5.0,
        travel_mode="walking",
        selection_reason="Main attraction",
        notes="Visit the Eiffel Tower",
        estimated_cost=25.00,
        estimated_cost_currency="USD",
    )


@pytest.fixture
def auth_client_with_user(db_session, test_user):
    """Create an authenticated TestClient for a specific user."""
    from app.core.security import create_access_token

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create access token for the test user
    access_token = create_access_token(test_user.id)

    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {access_token}"
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_client_with_other_user(db_session, other_user):
    """Create an authenticated TestClient for another user."""
    from app.core.security import create_access_token

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create access token for the other user
    access_token = create_access_token(other_user.id)

    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {access_token}"
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# Itinerary API Tests
# =============================================================================

class TestItineraryEndpoints:
    """Tests for itinerary endpoints."""

    def test_list_itineraries_by_trip_success(self, auth_client_with_user, test_trip, test_itinerary):
        """Test listing itineraries for a trip successfully."""
        response = auth_client_with_user.get(f"/itineraries/trips/{test_trip.id}")
        assert response.status_code == 200
        data = response.json()

        assert "itineraries" in data
        assert "count" in data
        assert data["count"] >= 1

        # Check that our test itinerary is in the list
        itinerary_ids = [it["id"] for it in data["itineraries"]]
        assert test_itinerary.id in itinerary_ids

    def test_list_itineraries_by_trip_ownership_violation(self, auth_client_with_user, other_user_trip):
        """Test that users cannot list itineraries for trips they don't own."""
        response = auth_client_with_user.get(f"/itineraries/trips/{other_user_trip.id}")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_list_itineraries_by_trip_not_found(self, auth_client_with_user):
        """Test listing itineraries for a non-existent trip."""
        response = auth_client_with_user.get("/itineraries/trips/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_list_itineraries_by_trip_pagination(self, auth_client_with_user, test_trip, db_session):
        """Test pagination for itineraries list."""
        # Create multiple itineraries for the test trip
        for i in range(5):
            ItineraryRepository.create(
                db=db_session,
                trip_id=test_trip.id,
                version=i + 2,  # Start from version 2
                status=ItineraryStatus.DRAFT,
            )

        # Test limit
        response = auth_client_with_user.get(f"/itineraries/trips/{test_trip.id}?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["itineraries"]) <= 3

    def test_get_itinerary_by_id_success(self, auth_client_with_user, test_itinerary):
        """Test getting an itinerary by ID successfully."""
        response = auth_client_with_user.get(f"/itineraries/{test_itinerary.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_itinerary.id
        assert data["trip_id"] == test_itinerary.trip_id
        assert data["version"] == test_itinerary.version
        assert data["status"] == test_itinerary.status.value
        assert data["total_duration_minutes"] == test_itinerary.total_duration_minutes

    def test_get_itinerary_by_id_ownership_violation(self, auth_client_with_user, other_user_itinerary):
        """Test that users cannot access itineraries they don't own."""
        response = auth_client_with_user.get(f"/itineraries/{other_user_itinerary.id}")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_get_itinerary_by_id_not_found(self, auth_client_with_user):
        """Test getting a non-existent itinerary by ID."""
        response = auth_client_with_user.get("/itineraries/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_get_itinerary_stops_success(self, auth_client_with_user, test_itinerary, test_itinerary_stop):
        """Test getting stops for an itinerary successfully."""
        response = auth_client_with_user.get(f"/itineraries/{test_itinerary.id}/stops")
        assert response.status_code == 200
        data = response.json()

        assert "stops" in data
        assert "count" in data
        assert data["count"] >= 1

        # Check that our test stop is in the list
        stop_ids = [s["id"] for s in data["stops"]]
        assert test_itinerary_stop.id in stop_ids

    def test_get_itinerary_stops_ownership_violation(self, auth_client_with_user, other_user_itinerary):
        """Test that users cannot access stops for itineraries they don't own."""
        response = auth_client_with_user.get(f"/itineraries/{other_user_itinerary.id}/stops")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_get_itinerary_stops_not_found(self, auth_client_with_user):
        """Test getting stops for a non-existent itinerary."""
        response = auth_client_with_user.get("/itineraries/99999/stops")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_get_itinerary_stops_empty(self, auth_client_with_user, test_trip, db_session):
        """Test getting stops for an itinerary with no stops."""
        # Create an itinerary without stops
        empty_itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=test_trip.id,
            version=10,
            status=ItineraryStatus.DRAFT,
        )

        response = auth_client_with_user.get(f"/itineraries/{empty_itinerary.id}/stops")
        assert response.status_code == 200
        data = response.json()
        assert data["stops"] == []
        assert data["count"] == 0

    def test_itinerary_response_structure(self, auth_client_with_user, test_itinerary):
        """Test that itinerary response has correct structure."""
        response = auth_client_with_user.get(f"/itineraries/{test_itinerary.id}")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "id", "trip_id", "version", "status", "total_duration_minutes",
            "estimated_travel_duration_minutes", "estimated_cost", "is_optimized",
            "stop_count", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_itinerary_stop_response_structure(self, auth_client_with_user, test_itinerary_stop):
        """Test that itinerary stop response has correct structure."""
        response = auth_client_with_user.get(f"/itineraries/{test_itinerary_stop.itinerary_id}/stops")
        assert response.status_code == 200
        data = response.json()

        # Find our test stop
        our_stop = next((s for s in data["stops"] if s["id"] == test_itinerary_stop.id), None)
        assert our_stop is not None

        # Check required fields
        required_fields = [
            "id", "itinerary_id", "destination_id", "sequence",
            "estimated_travel_duration_minutes", "estimated_travel_distance_km",
            "estimated_cost", "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in our_stop, f"Missing required field: {field}"

    def test_unauthenticated_access_to_itineraries(self, db_session):
        """Test that unauthenticated users cannot access itinerary endpoints."""
        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            # Test GET by trip without auth
            response = client.get("/itineraries/trips/1")
            assert response.status_code == 401

            # Test GET by ID without auth
            response = client.get("/itineraries/1")
            assert response.status_code == 401

            # Test GET stops without auth
            response = client.get("/itineraries/1/stops")
            assert response.status_code == 401

        app.dependency_overrides.clear()

    def test_itinerary_stop_count(self, auth_client_with_user, test_itinerary, test_itinerary_stop, db_session):
        """Test that itinerary stop_count is correct."""
        # Add another stop to the itinerary
        louvre = DestinationRepository.create(
            db=db_session,
            name="Louvre Museum",
            slug="louvre-museum",
            location_wkt="POINT(2.3354 48.8606)",
            category=DestinationCategory.CULTURAL,
        )

        # Create another stop
        ItineraryRepository.create_stop(
            db=db_session,
            itinerary_id=test_itinerary.id,
            destination_id=louvre.id,  # Louvre Museum
            sequence=2,
            visit_duration_minutes=120,
        )

        response = auth_client_with_user.get(f"/itineraries/{test_itinerary.id}")
        assert response.status_code == 200
        data = response.json()

        # Should have at least 2 stops now
        assert data["stop_count"] >= 2
