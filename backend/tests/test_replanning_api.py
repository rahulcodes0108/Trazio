"""Tests for the dynamic itinerary replanning API endpoint."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers import itineraries as itineraries_router
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.destination import DestinationCategory
from app.models.itinerary import ItineraryStatus
from app.models.trip import BudgetLevel, TransportMode, TripStatus
from app.models.user import UserStatus
from app.repositories.destination_repository import DestinationRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.user_repository import UserRepository
from app.services.replanning_service import ReplanningError


TEST_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@postgres:5432/trazio_test"
)

engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="module")
def test_db():
    """Create and drop database tables for this test module."""
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
    """Create the primary test user."""
    return UserRepository.create(
        db=db_session,
        email="replan-test@example.com",
        username="replan_test_user",
        hashed_password=hash_password("testpass123"),
        full_name="Replan Test User",
        status=UserStatus.ACTIVE,
        is_verified=False,
    )


@pytest.fixture
def other_user(db_session):
    """Create another user for ownership tests."""
    return UserRepository.create(
        db=db_session,
        email="replan-other@example.com",
        username="replan_other_user",
        hashed_password=hash_password("testpass123"),
        full_name="Other Replan User",
        status=UserStatus.ACTIVE,
        is_verified=False,
    )


@pytest.fixture
def test_trip(db_session, test_user):
    """Create a test trip."""
    return TripRepository.create(
        db=db_session,
        user_id=test_user.id,
        title="Replanning Test Trip",
        start_location="Paris",
        start_date="2023-07-01",
        end_date="2023-07-10",
        budget_level=BudgetLevel.MID_RANGE,
        transport_mode=TransportMode.MIXED,
        status=TripStatus.PLANNING,
    )


@pytest.fixture
def other_user_trip(db_session, other_user):
    """Create another user's trip."""
    return TripRepository.create(
        db=db_session,
        user_id=other_user.id,
        title="Other User Trip",
        start_location="Paris",
        start_date="2023-07-01",
        end_date="2023-07-10",
        budget_level=BudgetLevel.MID_RANGE,
        transport_mode=TransportMode.MIXED,
        status=TripStatus.PLANNING,
    )


@pytest.fixture
def test_destination(db_session):
    """Create the destination used as the unavailable source stop."""
    return DestinationRepository.create(
        db=db_session,
        name="Source Attraction",
        slug="replan-source-attraction",
        location_wkt="POINT(2.294481 48.858370)",
        category=DestinationCategory.ATTRACTION,
        description="Source destination",
        city="Paris",
        country="France",
    )


@pytest.fixture
def replacement_destination(db_session):
    """Create an eligible replacement destination."""
    return DestinationRepository.create(
        db=db_session,
        name="Replacement Attraction",
        slug="replan-replacement-attraction",
        location_wkt="POINT(2.300000 48.860000)",
        category=DestinationCategory.CULTURAL,
        description="Replacement destination",
        city="Paris",
        country="France",
    )


@pytest.fixture
def test_itinerary(db_session, test_trip):
    """Create the source itinerary."""
    return ItineraryRepository.create(
        db=db_session,
        trip_id=test_trip.id,
        version=1,
        status=ItineraryStatus.GENERATED,
        total_duration_minutes=480,
        estimated_travel_duration_minutes=120,
        estimated_cost=500.00,
        estimated_cost_currency="USD",
        notes="Source itinerary",
    )


@pytest.fixture
def test_itinerary_stop(db_session, test_itinerary, test_destination):
    """Create the unavailable stop on the source itinerary."""
    return ItineraryRepository.create_stop(
        db=db_session,
        itinerary_id=test_itinerary.id,
        destination_id=test_destination.id,
        sequence=1,
        planned_arrival=datetime(
            2023,
            7,
            1,
            9,
            0,
            tzinfo=timezone.utc,
        ),
        planned_departure=datetime(
            2023,
            7,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        visit_duration_minutes=180,
        estimated_travel_duration_minutes=30,
        estimated_travel_distance_km=5.0,
        travel_mode="walking",
        selection_reason="Primary attraction",
        notes="Source stop",
        estimated_cost=25.00,
        estimated_cost_currency="USD",
    )


@pytest.fixture
def other_user_itinerary(db_session, other_user_trip):
    """Create an itinerary owned by another user."""
    return ItineraryRepository.create(
        db=db_session,
        trip_id=other_user_trip.id,
        version=1,
        status=ItineraryStatus.DRAFT,
    )


@pytest.fixture
def auth_client_with_user(db_session, test_user):
    """Create an authenticated client for the source itinerary owner."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    access_token = create_access_token(test_user.id)

    with TestClient(app) as client:
        client.headers["Authorization"] = f"Bearer {access_token}"
        yield client

    app.dependency_overrides.clear()


class TestReplanningEndpoint:
    """Tests for POST /itineraries/{itinerary_id}/replan."""

    def test_replan_success(
        self,
        auth_client_with_user,
        test_itinerary,
        test_itinerary_stop,
        replacement_destination,
        db_session,
    ):
        """An owner can create a new itinerary version."""

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={
                "unavailable_destination_ids": [
                    test_itinerary_stop.destination_id
                ],
                "reason": "Destination became unavailable",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["id"] != test_itinerary.id
        assert data["trip_id"] == test_itinerary.trip_id
        assert data["version"] == test_itinerary.version + 1

        new_stops = ItineraryRepository.list_stops_by_itinerary(
            db=db_session,
            itinerary_id=data["id"],
        )

        destination_ids = [
            stop.destination_id for stop in new_stops
        ]

        assert test_itinerary_stop.destination_id not in destination_ids
        assert replacement_destination.id in destination_ids

        source = ItineraryRepository.get_by_id(
            db=db_session,
            itinerary_id=test_itinerary.id,
        )

        assert source.version == 1

    def test_replan_unauthenticated(
        self,
        db_session,
        test_itinerary,
        test_itinerary_stop,
    ):
        """Unauthenticated requests are rejected."""

        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/itineraries/{test_itinerary.id}/replan",
                    json={
                        "unavailable_destination_ids": [
                            test_itinerary_stop.destination_id
                        ]
                    },
                )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_replan_itinerary_not_found(
        self,
        auth_client_with_user,
    ):
        """Replanning a missing itinerary returns 404."""

        response = auth_client_with_user.post(
            "/itineraries/99999/replan",
            json={"unavailable_destination_ids": [1]},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_replan_ownership_violation(
        self,
        auth_client_with_user,
        other_user_itinerary,
    ):
        """Users cannot replan another user's itinerary."""

        response = auth_client_with_user.post(
            f"/itineraries/{other_user_itinerary.id}/replan",
            json={"unavailable_destination_ids": [1]},
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()

    def test_replan_empty_unavailable_ids(
        self,
        auth_client_with_user,
        test_itinerary,
    ):
        """An empty unavailable destination list is rejected."""

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={"unavailable_destination_ids": []},
        )

        assert response.status_code == 422

    def test_replan_invalid_destination_id(
        self,
        auth_client_with_user,
        test_itinerary,
    ):
        """Invalid destination IDs are rejected by validation."""

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={"unavailable_destination_ids": [0]},
        )

        assert response.status_code == 422

    def test_replan_destination_not_in_source_itinerary(
        self,
        auth_client_with_user,
        test_itinerary,
        db_session,
    ):
        """Unavailable destinations must belong to the source itinerary."""

        unrelated_destination = DestinationRepository.create(
            db=db_session,
            name="Unrelated Destination",
            slug="replan-unrelated-destination",
            location_wkt="POINT(2.310000 48.861000)",
            category=DestinationCategory.ATTRACTION,
            description="Unrelated destination",
            city="Paris",
            country="France",
        )

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={
                "unavailable_destination_ids": [
                    unrelated_destination.id
                ]
            },
        )

        assert response.status_code == 400
        assert "itinerary" in response.json()["detail"].lower()

    def test_replan_response_shape(
        self,
        auth_client_with_user,
        test_itinerary,
        test_itinerary_stop,
        replacement_destination,
    ):
        """Successful replanning returns the expected response."""

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={
                "unavailable_destination_ids": [
                    test_itinerary_stop.destination_id
                ]
            },
        )

        assert response.status_code == 201

        data = response.json()

        required_fields = {
            "id",
            "trip_id",
            "version",
            "status",
            "total_duration_minutes",
            "estimated_travel_duration_minutes",
            "estimated_cost",
            "is_optimized",
            "stop_count",
            "created_at",
            "updated_at",
        }

        assert required_fields.issubset(data.keys())

    def test_replan_engine_error_returns_400(
        self,
        auth_client_with_user,
        test_itinerary,
        test_itinerary_stop,
        monkeypatch,
    ):
        """Known replanning failures return 400."""

        def fail_replanning(*args, **kwargs):
            raise ReplanningError("No valid replanning solution")

        monkeypatch.setattr(
            itineraries_router,
            "replan_itinerary",
            fail_replanning,
        )

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={
                "unavailable_destination_ids": [
                    test_itinerary_stop.destination_id
                ]
            },
        )

        assert response.status_code == 400
        assert "No valid replanning solution" in response.json()["detail"]

    def test_replan_unexpected_error_returns_500(
        self,
        auth_client_with_user,
        test_itinerary,
        test_itinerary_stop,
        monkeypatch,
    ):
        """Unexpected replanning failures return 500."""

        def fail_replanning(*args, **kwargs):
            raise RuntimeError("Unexpected failure")

        monkeypatch.setattr(
            itineraries_router,
            "replan_itinerary",
            fail_replanning,
        )

        response = auth_client_with_user.post(
            f"/itineraries/{test_itinerary.id}/replan",
            json={
                "unavailable_destination_ids": [
                    test_itinerary_stop.destination_id
                ]
            },
        )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to replan itinerary."