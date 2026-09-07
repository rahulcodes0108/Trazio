"""Tests for trip API endpoints."""

from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.trip import Trip, TripStatus, TransportMode, BudgetLevel
from app.models.user import User, UserStatus
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
def test_trip(db_session, test_user):
    """Create a test trip."""
    return TripRepository.create(
        db=db_session,
        user_id=test_user.id,
        title="Summer Vacation",
        start_location="New York",
        start_date=date(2023, 7, 1),
        end_date=date(2023, 7, 10),
        budget_level=BudgetLevel.MID_RANGE,
        transport_mode=TransportMode.MIXED,
        status=TripStatus.DRAFT,
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
def other_user_trip(db_session, other_user):
    """Create a trip for another user."""
    return TripRepository.create(
        db=db_session,
        user_id=other_user.id,
        title="Other User's Trip",
        start_location="Los Angeles",
        start_date=date(2023, 8, 1),
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
# Trip API Tests
# =============================================================================

class TestTripEndpoints:
    """Tests for trip endpoints."""

    def test_create_trip_success(self, auth_client_with_user, test_user, db_session):
        """Test creating a new trip successfully."""
        trip_data = {
            "title": "Europe Tour",
            "start_location": "London",
            "start_date": "2023-06-15",
            "end_date": "2023-06-30",
            "description": "Tour through Europe",
            "budget_level": "mid_range",
            "transport_mode": "flight",
        }

        response = auth_client_with_user.post("/trips", json=trip_data)
        assert response.status_code == 201
        data = response.json()

        assert data["id"] > 0
        assert data["title"] == "Europe Tour"
        assert data["start_location"] == "London"
        assert data["start_date"] == "2023-06-15"
        assert data["user_id"] == test_user.id
        assert data["status"] == "draft"

    def test_create_trip_missing_required_fields(self, auth_client_with_user):
        """Test creating a trip with missing required fields."""
        trip_data = {
            "title": "Missing Fields Trip",
            # Missing start_location and start_date
        }

        response = auth_client_with_user.post("/trips", json=trip_data)
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data

    def test_list_trips_success(self, auth_client_with_user, test_user, test_trip):
        """Test listing trips for a user."""
        response = auth_client_with_user.get("/trips")
        assert response.status_code == 200
        data = response.json()

        assert "trips" in data
        assert "count" in data
        assert data["count"] >= 1

        # Check that our test trip is in the list
        trip_ids = [t["id"] for t in data["trips"]]
        assert test_trip.id in trip_ids

    def test_list_trips_only_own(self, auth_client_with_user, test_user, other_user_trip):
        """Test that users can only see their own trips."""
        response = auth_client_with_user.get("/trips")
        assert response.status_code == 200
        data = response.json()

        # Ensure the other user's trip is not in the list
        other_trip_ids = [t["id"] for t in data["trips"] if t["id"] == other_user_trip.id]
        assert len(other_trip_ids) == 0

    def test_list_trips_pagination(self, auth_client_with_user, test_user, db_session):
        """Test pagination for trips list."""
        # Create multiple trips for the test user
        for i in range(15):
            TripRepository.create(
                db=db_session,
                user_id=test_user.id,
                title=f"Trip {i}",
                start_location="Test City",
                start_date=date(2023, 1, 1),
            )

        # Test limit
        response = auth_client_with_user.get("/trips?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trips"]) <= 5

        # Test skip
        response = auth_client_with_user.get("/trips?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["trips"]) <= 5

    def test_get_trip_by_id_success(self, auth_client_with_user, test_user, test_trip):
        """Test getting a trip by ID successfully."""
        response = auth_client_with_user.get(f"/trips/{test_trip.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_trip.id
        assert data["title"] == test_trip.title
        assert data["user_id"] == test_user.id
        assert data["start_location"] == test_trip.start_location

    def test_get_trip_by_id_not_found(self, auth_client_with_user):
        """Test getting a non-existent trip by ID."""
        response = auth_client_with_user.get("/trips/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_get_trip_by_id_ownership_violation(self, auth_client_with_user, other_user_trip):
        """Test that users cannot access trips owned by others."""
        response = auth_client_with_user.get(f"/trips/{other_user_trip.id}")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_update_trip_success(self, auth_client_with_user, test_user, test_trip):
        """Test updating a trip successfully."""
        update_data = {
            "title": "Updated Summer Vacation",
            "description": "Updated description",
            "status": "planning"
        }

        response = auth_client_with_user.patch(f"/trips/{test_trip.id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_trip.id
        assert data["title"] == "Updated Summer Vacation"
        assert data["description"] == "Updated description"
        assert data["status"] == "planning"

    def test_update_trip_ownership_violation(self, auth_client_with_user, other_user_trip):
        """Test that users cannot update trips owned by others."""
        update_data = {"title": "Unauthorized Update"}

        response = auth_client_with_user.patch(f"/trips/{other_user_trip.id}", json=update_data)
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_update_trip_not_found(self, auth_client_with_user):
        """Test updating a non-existent trip."""
        update_data = {"title": "Update Non-existent"}

        response = auth_client_with_user.patch("/trips/99999", json=update_data)
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_delete_trip_success(self, auth_client_with_user, test_user, test_trip, db_session):
        """Test deleting a trip successfully."""
        response = auth_client_with_user.delete(f"/trips/{test_trip.id}")
        assert response.status_code == 200
        data = response.json()
        assert "detail" in data
        assert f"Trip with ID {test_trip.id}" in data["detail"]

        # Verify the trip is actually deleted
        deleted_trip = TripRepository.get_by_id(db=db_session, trip_id=test_trip.id)
        assert deleted_trip is None

    def test_delete_trip_ownership_violation(self, auth_client_with_user, other_user_trip):
        """Test that users cannot delete trips owned by others."""
        response = auth_client_with_user.delete(f"/trips/{other_user_trip.id}")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "permission" in data["detail"]

    def test_delete_trip_not_found(self, auth_client_with_user):
        """Test deleting a non-existent trip."""
        response = auth_client_with_user.delete("/trips/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_trip_response_structure(self, auth_client_with_user, test_trip):
        """Test that trip response has correct structure."""
        response = auth_client_with_user.get(f"/trips/{test_trip.id}")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "id", "user_id", "title", "start_location", "start_date",
            "budget_level", "transport_mode", "status", "is_public",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_unauthenticated_access_to_trips(self, db_session):
        """Test that unauthenticated users cannot access trip endpoints."""
        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app) as client:
            # Test POST without auth
            response = client.post("/trips", json={
                "title": "Test",
                "start_location": "Test City",
                "start_date": "2023-01-01"
            })
            assert response.status_code == 401

            # Test GET all without auth
            response = client.get("/trips")
            assert response.status_code == 401

            # Test GET by ID without auth
            response = client.get("/trips/1")
            assert response.status_code == 401

        app.dependency_overrides.clear()
