"""Tests for user personalization and hybrid recommendation signals."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.destination import Destination, DestinationCategory
from app.models.feedback import Feedback, FeedbackType
from app.models.user import User
from app.services.personalization import (
    PersonalizationProfile,
    build_user_profile,
    explicit_preference_score,
    hybrid_personalization_score,
    personalized_category_score,
    personalization_explanation,
)


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
    """Create test database tables for the personalization tests."""
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

    if transaction.is_active:
        transaction.rollback()

    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="personalization@example.com",
        username="personalization_user",
        hashed_password="test_hash",
        full_name="Personalization Test User",
    )

    db_session.add(user)
    db_session.flush()

    return user


def make_trip(
    *,
    user_id: int = 1,
    categories: list[str] | None = None,
):
    """Create a minimal trip for personalization tests."""
    from app.models.trip import Trip

    return Trip(
        id=1,
        user_id=user_id,
        title="Personalization Test Trip",
        start_location="Chennai",
        start_date="2026-09-15",
        preferences={
            "categories": categories or [],
        },
    )


def make_destination(
    *,
    destination_id: int = 1,
    category: DestinationCategory = DestinationCategory.CULTURAL,
) -> Destination:
    """Create a minimal destination for personalization tests."""
    return Destination(
        id=destination_id,
        name=f"Destination {destination_id}",
        slug=f"destination-{destination_id}",
        location="POINT(80.2707 13.0827)",
        category=category,
        popularity_score=80,
        entry_fee=0,
        average_visit_duration_minutes=60,
        is_active=True,
    )


def test_empty_history_produces_neutral_profile(db_session, test_user):
    """A user with no ratings should have neutral personalization."""
    profile = build_user_profile(db_session, test_user)

    assert profile.category_affinity == {}
    assert profile.rated_destination_ids == frozenset()
    assert profile.interaction_count == 0


def test_rating_normalization(db_session, test_user):
    """Ratings should normalize from 1-5 into 0.0-1.0."""
    destinations = [
        make_destination(
            destination_id=10,
            category=DestinationCategory.ENTERTAINMENT,
        ),
        make_destination(
            destination_id=11,
            category=DestinationCategory.NATURE,
        ),
        make_destination(
            destination_id=12,
            category=DestinationCategory.CULTURAL,
        ),
    ]

    db_session.add_all(destinations)
    db_session.flush()

    ratings = [
        (10, 1),
        (11, 5),
        (12, 2),
    ]

    for destination_id, rating in ratings:
        db_session.add(
            Feedback(
                user_id=test_user.id,
                destination_id=destination_id,
                feedback_type=FeedbackType.RATING,
                rating=rating,
                title="Personalization test",
                content="Controlled test feedback",
                is_anonymous=False,
                is_public=False,
            )
        )

    db_session.flush()

    profile = build_user_profile(db_session, test_user)

    assert profile.category_affinity["entertainment"] == 0.0
    assert profile.category_affinity["nature"] == 1.0
    assert profile.category_affinity["cultural"] == 0.25
    assert profile.interaction_count == 3
    assert profile.rated_destination_ids == frozenset({10, 11, 12})


def test_personalized_category_score_uses_learned_affinity():
    """Known category affinity should become a 0-100 score."""
    profile = PersonalizationProfile(
        category_affinity={
            "nature": 1.0,
            "cultural": 0.25,
        },
        rated_destination_ids=frozenset(),
        interaction_count=2,
    )

    nature = make_destination(category=DestinationCategory.NATURE)
    cultural = make_destination(category=DestinationCategory.CULTURAL)
    entertainment = make_destination(
        category=DestinationCategory.ENTERTAINMENT
    )

    assert personalized_category_score(nature, profile) == 100.0
    assert personalized_category_score(cultural, profile) == 25.0
    assert personalized_category_score(entertainment, profile) == 50.0


def test_explicit_preference_score_matches_requested_category():
    """Explicit trip preferences should receive a full matching score."""
    trip = make_trip(categories=["nature"])

    nature = make_destination(category=DestinationCategory.NATURE)
    cultural = make_destination(category=DestinationCategory.CULTURAL)

    assert explicit_preference_score(nature, trip) == 100.0
    assert explicit_preference_score(cultural, trip) == 0.0


def test_explicit_preference_score_is_neutral_without_preferences():
    """Missing explicit preferences should remain neutral."""
    trip = make_trip(categories=[])

    destination = make_destination(category=DestinationCategory.NATURE)

    assert explicit_preference_score(destination, trip) == 50.0


def test_hybrid_score_combines_explicit_and_learned_signals():
    """Hybrid scoring should combine explicit and historical preferences."""
    trip = make_trip(categories=["nature"])

    profile = PersonalizationProfile(
        category_affinity={"nature": 1.0},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    destination = make_destination(category=DestinationCategory.NATURE)

    assert hybrid_personalization_score(
        destination,
        trip,
        profile,
    ) == 100.0


def test_hybrid_score_can_distinguish_historical_affinity():
    """Historical affinity should affect the hybrid score."""
    trip = make_trip(categories=["nature"])

    strong_profile = PersonalizationProfile(
        category_affinity={"nature": 1.0},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    weak_profile = PersonalizationProfile(
        category_affinity={"nature": 0.0},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    destination = make_destination(category=DestinationCategory.NATURE)

    strong_score = hybrid_personalization_score(
        destination,
        trip,
        strong_profile,
    )

    weak_score = hybrid_personalization_score(
        destination,
        trip,
        weak_profile,
    )

    assert strong_score == 100.0
    assert weak_score == 65.0
    assert strong_score > weak_score


def test_personalization_explanation_mentions_current_interest():
    """Matching explicit preferences should be explained."""
    trip = make_trip(categories=["nature"])

    profile = PersonalizationProfile(
        category_affinity={"nature": 1.0},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    destination = make_destination(category=DestinationCategory.NATURE)

    explanation = personalization_explanation(
        destination,
        trip,
        profile,
    )

    assert explanation is not None
    assert "matches your current interests" in explanation


def test_personalization_explanation_mentions_high_historical_affinity():
    """High learned affinity should appear in the explanation."""
    trip = make_trip(categories=[])

    profile = PersonalizationProfile(
        category_affinity={"nature": 1.0},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    destination = make_destination(category=DestinationCategory.NATURE)

    explanation = personalization_explanation(
        destination,
        trip,
        profile,
    )

    assert explanation is not None
    assert "matches categories you have rated highly" in explanation


def test_personalization_explanation_mentions_weaker_affinity():
    """Low learned affinity should be transparently explained."""
    trip = make_trip(categories=[])

    profile = PersonalizationProfile(
        category_affinity={"nature": 0.25},
        rated_destination_ids=frozenset(),
        interaction_count=1,
    )

    destination = make_destination(category=DestinationCategory.NATURE)

    explanation = personalization_explanation(
        destination,
        trip,
        profile,
    )

    assert explanation is not None
    assert "weaker historical preference affinity" in explanation
