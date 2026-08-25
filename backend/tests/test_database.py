"""Database and domain model tests for Trazio."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.destination import (
    AccessibilityLevel,
    DestinationCategory,
    DestinationSourceStatus,
)
from app.models.feedback import Feedback, FeedbackType
from app.models.itinerary import ItineraryStatus
from app.models.session import Session, SessionStatus
from app.models.trip import BudgetLevel, TransportMode, TripStatus
from app.models.user import UserStatus
from app.repositories.destination_repository import DestinationRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.user_repository import UserRepository

# Test database setup
# Use 'postgres' as host for Docker, 'localhost' for local development
# Docker container name is 'trazio-postgres' but from host we use 'localhost'
TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/trazio_test"

# Create test engine and session factory
engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    """Create and drop test database tables for each test module."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables with CASCADE to handle foreign key constraints
    # This is safer than dropping the entire public schema
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


# =============================================================================
# MODEL CREATION TESTS
# =============================================================================

class TestUserModel:
    """Tests for User model creation and constraints."""

    def test_create_user(self, db_session):
        """Test creating a user with required fields."""
        user = UserRepository.create(
            db=db_session,
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_secret",
        )
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.status == UserStatus.ACTIVE
        assert user.is_verified is False
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_user_with_optional_fields(self, db_session):
        """Test creating a user with optional fields."""
        user = UserRepository.create(
            db=db_session,
            email="test2@example.com",
            username="testuser2",
            hashed_password="hashed_secret2",
            full_name="Test User Two",
        )
        assert user.full_name == "Test User Two"

    def test_unique_email_constraint(self, db_session):
        """Test that email must be unique."""
        UserRepository.create(
            db=db_session,
            email="unique@example.com",
            username="user1",
            hashed_password="hash1",
        )
        with pytest.raises(exc.IntegrityError):  # IntegrityError
            UserRepository.create(
                db=db_session,
                email="unique@example.com",
                username="user2",
                hashed_password="hash2",
            )
        db_session.rollback()

    def test_unique_username_constraint(self, db_session):
        """Test that username must be unique."""
        UserRepository.create(
            db=db_session,
            email="email1@example.com",
            username="uniqueuser",
            hashed_password="hash1",
        )
        with pytest.raises(exc.IntegrityError):
            UserRepository.create(
                db=db_session,
                email="email2@example.com",
                username="uniqueuser",
                hashed_password="hash2",
            )
        db_session.rollback()


class TestSessionModel:
    """Tests for Session model creation and constraints."""

    def test_create_session(self, db_session):
        """Test creating a session."""
        user = UserRepository.create(
            db=db_session,
            email="sessionuser@example.com",
            username="sessionuser",
            hashed_password="hash",
        )
        expires_at = datetime.now(UTC) + timedelta(days=7)
        session = Session(
            user_id=user.id,
            session_token="unique_token_123",
            expires_at=expires_at,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.status == SessionStatus.ACTIVE

    def test_unique_session_token_constraint(self, db_session):
        """Test that session token must be unique."""
        user = UserRepository.create(
            db=db_session,
            email="tokenuser@example.com",
            username="tokenuser",
            hashed_password="hash",
        )
        expires_at = datetime.now(UTC) + timedelta(days=7)
        session1 = Session(
            user_id=user.id,
            session_token="token_123",
            expires_at=expires_at,
        )
        db_session.add(session1)
        db_session.commit()

        session2 = Session(
            user_id=user.id,
            session_token="token_123",
            expires_at=expires_at,
        )
        db_session.add(session2)
        with pytest.raises(exc.IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestDestinationModel:
    """Tests for Destination model creation and PostGIS geometry."""

    def test_create_destination_with_point(self, db_session):
        """Test creating a destination with PostGIS point geometry."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Test Destination",
            slug="test-destination",
            location_wkt="POINT(-73.9857 40.7484)",  # New York coordinates
            description="A test destination",
            category=DestinationCategory.ATTRACTION,
        )
        assert destination.id is not None
        assert destination.name == "Test Destination"
        assert destination.slug == "test-destination"
        assert destination.category == DestinationCategory.ATTRACTION
        assert destination.popularity_score == 0.0
        assert destination.is_active is True

    def test_create_destination_with_all_fields(self, db_session):
        """Test creating a destination with all optional fields."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Full Destination",
            slug="full-destination",
            location_wkt="POINT(2.3522 48.8566)",  # Paris
            description="Full test",
            category=DestinationCategory.RESTAURANT,
            address_line1="123 Main St",
            city="Paris",
            country="France",
            opening_hours="9:00-17:00",
            entry_fee=10.0,
            entry_fee_currency="EUR",
            average_visit_duration_minutes=60,
            accessibility=AccessibilityLevel.FULLY_ACCESSIBLE,
            popularity_score=85.5,
        )
        assert destination.city == "Paris"
        assert destination.entry_fee == 10.0
        assert destination.accessibility == AccessibilityLevel.FULLY_ACCESSIBLE

    def test_unique_slug_constraint(self, db_session):
        """Test that slug must be unique."""
        DestinationRepository.create(
            db=db_session,
            name="Dest 1",
            slug="unique-slug",
            location_wkt="POINT(0 0)",
        )
        with pytest.raises(exc.IntegrityError):
            DestinationRepository.create(
                db=db_session,
                name="Dest 2",
                slug="unique-slug",
                location_wkt="POINT(1 1)",
            )
        db_session.rollback()

    def test_popularity_score_constraint(self, db_session):
        """Test that popularity score must be between 0 and 100."""
        with pytest.raises(exc.IntegrityError):
            DestinationRepository.create(
                db=db_session,
                name="Invalid Score",
                slug="invalid-score",
                location_wkt="POINT(0 0)",
                popularity_score=150.0,
            )
        db_session.rollback()

        with pytest.raises(exc.IntegrityError):
            DestinationRepository.create(
                db=db_session,
                name="Invalid Score 2",
                slug="invalid-score-2",
                location_wkt="POINT(0 0)",
                popularity_score=-10.0,
            )
        db_session.rollback()


class TestDestinationSourceModel:
    """Tests for DestinationSource model and provenance tracking."""

    def test_create_destination_source(self, db_session):
        """Test creating a destination source."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Source Test Dest",
            slug="source-test-dest",
            location_wkt="POINT(0 0)",
        )
        source = DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Test Source",
            source_reference="ref_123",
            verification_status=DestinationSourceStatus.VERIFIED,
            trust_score=95.0,
        )
        assert source.id is not None
        assert source.destination_id == destination.id
        assert source.source_name == "Test Source"
        assert source.trust_score == 95.0

    def test_get_sources_by_destination(self, db_session):
        """Test retrieving sources for a destination."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Multi Source Dest",
            slug="multi-source-dest",
            location_wkt="POINT(0 0)",
        )
        DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Source 1",
            source_reference="ref_1",
        )
        DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Source 2",
            source_reference="ref_2",
        )

        sources = DestinationRepository.get_sources_by_destination(
            db=db_session,
            destination_id=destination.id,
        )
        assert len(sources) == 2

    def test_trust_score_constraint(self, db_session):
        """Test that trust score must be between 0 and 100."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Trust Test",
            slug="trust-test",
            location_wkt="POINT(0 0)",
        )
        with pytest.raises(exc.IntegrityError):
            DestinationRepository.create_source(
                db=db_session,
                destination_id=destination.id,
                source_name="Invalid Trust",
                source_reference="ref_invalid",
                trust_score=150.0,
            )
        db_session.rollback()


class TestTripModel:
    """Tests for Trip model creation and constraints."""

    def test_create_trip(self, db_session):
        """Test creating a trip with required fields."""
        user = UserRepository.create(
            db=db_session,
            email="tripuser@example.com",
            username="tripuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Test Trip",
            start_location="New York",
            start_date=date(2026, 1, 1),
        )
        assert trip.id is not None
        assert trip.title == "Test Trip"
        assert trip.start_location == "New York"
        assert trip.status == TripStatus.DRAFT
        assert trip.budget_level == BudgetLevel.MID_RANGE

    def test_create_trip_with_all_fields(self, db_session):
        """Test creating a trip with all optional fields."""
        user = UserRepository.create(
            db=db_session,
            email="fulltrip@example.com",
            username="fulltripuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Full Trip",
            start_location="Paris",
            start_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_date=date(2026, 6, 10),
            end_time=time(18, 0),
            available_duration_minutes=480,
            budget_level=BudgetLevel.LUXURY,
            budget_amount=5000.0,
            budget_currency="USD",
            transport_mode=TransportMode.DRIVING,
            is_public=True,
        )
        assert trip.budget_amount == 5000.0
        assert trip.transport_mode == TransportMode.DRIVING

    def test_dates_valid_constraint(self, db_session):
        """Test that end_date must be >= start_date."""
        user = UserRepository.create(
            db=db_session,
            email="dateuser@example.com",
            username="dateuser",
            hashed_password="hash",
        )
        with pytest.raises(exc.IntegrityError):
            TripRepository.create(
                db=db_session,
                user_id=user.id,
                title="Invalid Dates",
                start_location="City",
                start_date=date(2026, 12, 31),
                end_date=date(2026, 1, 1),  # Before start_date
            )
        db_session.rollback()


class TestItineraryModel:
    """Tests for Itinerary model and versioning."""

    def test_create_itinerary(self, db_session):
        """Test creating an itinerary."""
        user = UserRepository.create(
            db=db_session,
            email="itineraryuser@example.com",
            username="itineraryuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Itinerary Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        assert itinerary.id is not None
        assert itinerary.trip_id == trip.id
        assert itinerary.version == 1
        assert itinerary.status == ItineraryStatus.DRAFT

    def test_itinerary_version_uniqueness(self, db_session):
        """Test that (trip_id, version) must be unique."""
        user = UserRepository.create(
            db=db_session,
            email="versionuser@example.com",
            username="versionuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Version Test Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        with pytest.raises(exc.IntegrityError):
            ItineraryRepository.create(
                db=db_session,
                trip_id=trip.id,
                version=1,  # Duplicate version
            )
        db_session.rollback()

    def test_multiple_versions_per_trip(self, db_session):
        """Test that a trip can have multiple itinerary versions."""
        user = UserRepository.create(
            db=db_session,
            email="multiuser@example.com",
            username="multiuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Multi Version Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=1)
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=2)
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=3)

        itineraries = ItineraryRepository.list_by_trip(db=db_session, trip_id=trip.id)
        assert len(itineraries) == 3
        assert [i.version for i in itineraries] == [3, 2, 1]  # Ordered descending

    def test_get_latest_itinerary(self, db_session):
        """Test retrieving the latest itinerary for a trip."""
        user = UserRepository.create(
            db=db_session,
            email="latestuser@example.com",
            username="latestuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Latest Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=1)
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=5)
        ItineraryRepository.create(db=db_session, trip_id=trip.id, version=3)

        latest = ItineraryRepository.get_latest_by_trip(db=db_session, trip_id=trip.id)
        assert latest.version == 5

    def test_itinerary_stop_creation(self, db_session):
        """Test creating itinerary stops."""
        user = UserRepository.create(
            db=db_session,
            email="stopuser@example.com",
            username="stopuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Stop Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        destination = DestinationRepository.create(
            db=db_session,
            name="Stop Destination",
            slug="stop-destination",
            location_wkt="POINT(0 0)",
        )

        stop = ItineraryRepository.create_stop(
            db=db_session,
            itinerary_id=itinerary.id,
            destination_id=destination.id,
            sequence=1,
            visit_duration_minutes=60,
        )
        assert stop.id is not None
        assert stop.sequence == 1

    def test_list_stops_ordered_by_sequence(self, db_session):
        """Test that stops are returned ordered by sequence."""
        user = UserRepository.create(
            db=db_session,
            email="sequser@example.com",
            username="sequser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Sequence Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        dest1 = DestinationRepository.create(
            db=db_session, name="Dest 1", slug="dest-1", location_wkt="POINT(0 0)"
        )
        dest2 = DestinationRepository.create(
            db=db_session, name="Dest 2", slug="dest-2", location_wkt="POINT(1 1)"
        )
        dest3 = DestinationRepository.create(
            db=db_session, name="Dest 3", slug="dest-3", location_wkt="POINT(2 2)"
        )

        ItineraryRepository.create_stop(db=db_session, itinerary_id=itinerary.id, destination_id=dest3.id, sequence=3)
        ItineraryRepository.create_stop(db=db_session, itinerary_id=itinerary.id, destination_id=dest1.id, sequence=1)
        ItineraryRepository.create_stop(db=db_session, itinerary_id=itinerary.id, destination_id=dest2.id, sequence=2)

        stops = ItineraryRepository.list_stops_by_itinerary(db=db_session, itinerary_id=itinerary.id)
        assert len(stops) == 3
        assert [s.sequence for s in stops] == [1, 2, 3]


class TestFeedbackModel:
    """Tests for Feedback model."""

    def test_create_feedback_for_destination(self, db_session):
        """Test creating feedback for a destination."""
        user = UserRepository.create(
            db=db_session,
            email="feedbackuser@example.com",
            username="feedbackuser",
            hashed_password="hash",
        )
        destination = DestinationRepository.create(
            db=db_session,
            name="Feedback Dest",
            slug="feedback-dest",
            location_wkt="POINT(0 0)",
        )
        feedback = Feedback(
            user_id=user.id,
            destination_id=destination.id,
            feedback_type=FeedbackType.RATING,
            rating=5,
            title="Great place!",
            content="I loved visiting this destination.",
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        assert feedback.id is not None
        assert feedback.rating == 5

    def test_create_feedback_for_trip(self, db_session):
        """Test creating feedback for a trip."""
        user = UserRepository.create(
            db=db_session,
            email="tripfeedback@example.com",
            username="tripfeedback",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Feedback Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        feedback = Feedback(
            user_id=user.id,
            trip_id=trip.id,
            feedback_type=FeedbackType.REVIEW,
            title="Great trip!",
            content="The itinerary was perfect.",
            rating=4,
        )
        db_session.add(feedback)
        db_session.commit()

        assert feedback.trip_id == trip.id


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================

class TestRelationships:
    """Tests for model relationships."""

    def test_user_sessions_relationship(self, db_session):
        """Test User to Session relationship."""
        user = UserRepository.create(
            db=db_session,
            email="reluser@example.com",
            username="reluser",
            hashed_password="hash",
        )
        expires_at = datetime.now(UTC) + timedelta(days=7)
        session1 = Session(
            user_id=user.id,
            session_token="token_1",
            expires_at=expires_at,
        )
        session2 = Session(
            user_id=user.id,
            session_token="token_2",
            expires_at=expires_at,
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        db_session.refresh(user)
        assert len(user.sessions) == 2

    def test_user_trips_relationship(self, db_session):
        """Test User to Trip relationship."""
        user = UserRepository.create(
            db=db_session,
            email="tripreluser@example.com",
            username="tripreluser",
            hashed_password="hash",
        )
        _trip1 = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Trip 1",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        _trip2 = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Trip 2",
            start_location="City",
            start_date=date(2026, 2, 1),
        )

        db_session.refresh(user)
        assert len(user.trips) == 2

    def test_trip_itineraries_relationship(self, db_session):
        """Test Trip to Itinerary relationship."""
        user = UserRepository.create(
            db=db_session,
            email="itinereluser@example.com",
            username="itinereluser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Itinerary Relationship Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        _itinerary1 = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        _itinerary2 = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=2,
        )

        db_session.refresh(trip)
        assert len(trip.itineraries) == 2

    def test_itinerary_stops_relationship(self, db_session):
        """Test Itinerary to ItineraryStop relationship."""
        user = UserRepository.create(
            db=db_session,
            email="stopreluser@example.com",
            username="stopreluser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Stop Relationship Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        dest1 = DestinationRepository.create(
            db=db_session, name="Stop Rel Dest 1", slug="stop-rel-1", location_wkt="POINT(0 0)"
        )
        dest2 = DestinationRepository.create(
            db=db_session, name="Stop Rel Dest 2", slug="stop-rel-2", location_wkt="POINT(1 1)"
        )

        ItineraryRepository.create_stop(
            db=db_session, itinerary_id=itinerary.id, destination_id=dest1.id, sequence=1
        )
        ItineraryRepository.create_stop(
            db=db_session, itinerary_id=itinerary.id, destination_id=dest2.id, sequence=2
        )

        db_session.refresh(itinerary)
        assert len(itinerary.stops) == 2

    def test_destination_itinerary_stops_relationship(self, db_session):
        """Test Destination to ItineraryStop relationship."""
        user = UserRepository.create(
            db=db_session,
            email="deststoprel@example.com",
            username="deststoprel",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Dest Stop Rel Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )
        destination = DestinationRepository.create(
            db=db_session,
            name="Destination for stops",
            slug="dest-for-stops",
            location_wkt="POINT(0 0)",
        )

        _stop1 = ItineraryRepository.create_stop(
            db=db_session, itinerary_id=itinerary.id, destination_id=destination.id, sequence=1
        )
        _stop2 = ItineraryRepository.create_stop(
            db=db_session, itinerary_id=itinerary.id, destination_id=destination.id, sequence=2
        )

        db_session.refresh(destination)
        assert len(destination.itinerary_stops) == 2

    def test_destination_sources_relationship(self, db_session):
        """Test Destination to DestinationSource relationship."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Source Relationship Dest",
            slug="source-rel-dest",
            location_wkt="POINT(0 0)",
        )
        DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Source A",
            source_reference="ref_a",
        )
        DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Source B",
            source_reference="ref_b",
        )

        db_session.refresh(destination)
        assert len(destination.sources) == 2

    def test_cascade_delete_user(self, db_session):
        """Test that deleting a user cascades to sessions and trips."""
        user = UserRepository.create(
            db=db_session,
            email="cascadeuser@example.com",
            username="cascadeuser",
            hashed_password="hash",
        )
        trip = TripRepository.create(
            db=db_session,
            user_id=user.id,
            title="Cascade Trip",
            start_location="City",
            start_date=date(2026, 1, 1),
        )
        itinerary = ItineraryRepository.create(
            db=db_session,
            trip_id=trip.id,
            version=1,
        )

        user_id = user.id
        trip_id = trip.id
        itinerary_id = itinerary.id

        db_session.delete(user)
        db_session.commit()

        # Verify user is deleted
        assert UserRepository.get_by_id(db=db_session, user_id=user_id) is None
        # Verify trip is cascade deleted
        assert TripRepository.get_by_id(db=db_session, trip_id=trip_id) is None
        # Verify itinerary is cascade deleted
        assert ItineraryRepository.get_by_id(db=db_session, itinerary_id=itinerary_id) is None

    def test_cascade_delete_destination(self, db_session):
        """Test that deleting a destination cascades to sources and stops."""
        destination = DestinationRepository.create(
            db=db_session,
            name="Cascade Dest",
            slug="cascade-dest",
            location_wkt="POINT(0 0)",
        )
        DestinationRepository.create_source(
            db=db_session,
            destination_id=destination.id,
            source_name="Cascade Source",
            source_reference="cascade_ref",
        )

        destination_id = destination.id

        db_session.delete(destination)
        db_session.commit()

        # Verify destination is deleted
        assert DestinationRepository.get_by_id(db=db_session, destination_id=destination_id) is None
        # Verify source is cascade deleted
        sources = DestinationRepository.get_sources_by_destination(
            db=db_session, destination_id=destination_id
        )
        assert len(sources) == 0
