"""Tests for destination API endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.destination import Destination, DestinationCategory, AccessibilityLevel
from app.models.user import User, UserStatus
from app.repositories.destination_repository import DestinationRepository
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
        popularity_score=95.5,
        accessibility=AccessibilityLevel.FULLY_ACCESSIBLE,
    )


@pytest.fixture
def test_destination_inactive(db_session):
    """Create a test inactive destination."""
    return DestinationRepository.create(
        db=db_session,
        name="Inactive Destination",
        slug="inactive-destination",
        location_wkt="POINT(0.0 0.0)",
        category=DestinationCategory.OTHER,
        is_active=False,
    )


@pytest.fixture
def auth_client(db_session):
    """Create a TestClient using the test database session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# Destination API Tests
# =============================================================================

class TestDestinationEndpoints:
    """Tests for destination endpoints."""

    def test_list_destinations_empty(self, auth_client, db_session):
        """Test listing destinations when none exist (active ones only)."""
        # Clear any existing active destinations
        db_session.query(Destination).filter(Destination.is_active == True).delete()
        db_session.commit()

        response = auth_client.get("/destinations")
        assert response.status_code == 200
        data = response.json()
        assert "destinations" in data
        assert "count" in data
        assert data["count"] == 0
        assert data["destinations"] == []

    def test_list_destinations_success(self, auth_client, test_destination, db_session):
        """Test listing destinations successfully."""
        response = auth_client.get("/destinations")
        assert response.status_code == 200
        data = response.json()
        assert "destinations" in data
        assert "count" in data
        assert data["count"] >= 1

        # Check that our test destination is in the list
        destination_ids = [d["id"] for d in data["destinations"]]
        assert test_destination.id in destination_ids

        # Check that inactive destinations are not included
        inactive_dest_ids = [d["id"] for d in data["destinations"] if not d["is_active"]]
        assert len(inactive_dest_ids) == 0

    def test_list_destinations_pagination(self, auth_client, db_session):
        """Test pagination for destinations list."""
        # Create multiple destinations
        for i in range(15):
            DestinationRepository.create(
                db=db_session,
                name=f"Destination {i}",
                slug=f"destination-{i}",
                location_wkt=f"POINT({i}.0 {i}.0)",
                category=DestinationCategory.ATTRACTION,
            )

        # Test limit
        response = auth_client.get("/destinations?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["destinations"]) <= 5

        # Test skip
        response = auth_client.get("/destinations?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["destinations"]) <= 5

    def test_get_destination_by_id_success(self, auth_client, test_destination):
        """Test getting a destination by ID successfully."""
        response = auth_client.get(f"/destinations/{test_destination.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_destination.id
        assert data["name"] == test_destination.name
        assert data["slug"] == test_destination.slug
        assert data["category"] == test_destination.category.value
        assert data["city"] == test_destination.city
        assert data["country"] == test_destination.country
        assert data["popularity_score"] == test_destination.popularity_score
        assert data["is_active"] is True

    def test_get_destination_by_id_not_found(self, auth_client):
        """Test getting a non-existent destination by ID."""
        response = auth_client.get("/destinations/99999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_get_destination_by_slug_success(self, auth_client, test_destination):
        """Test getting a destination by slug successfully."""
        response = auth_client.get(f"/destinations/slug/{test_destination.slug}")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_destination.id
        assert data["name"] == test_destination.name
        assert data["slug"] == test_destination.slug

    def test_get_destination_by_slug_not_found(self, auth_client):
        """Test getting a non-existent destination by slug."""
        response = auth_client.get("/destinations/slug/nonexistent-slug")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]

    def test_destination_response_structure(self, auth_client, test_destination):
        """Test that destination response has correct structure."""
        response = auth_client.get(f"/destinations/{test_destination.id}")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "id", "name", "slug", "category", "location", "is_active",
            "created_at", "updated_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check that timestamps are in expected format
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_destination_location_format(self, auth_client, test_destination):
        """Test that destination location is returned as string."""
        response = auth_client.get(f"/destinations/{test_destination.id}")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["location"], str)
        assert "POINT" in data["location"]
