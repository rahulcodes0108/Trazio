"""Session model and service tests for Trazio."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.session import Session, SessionStatus
from app.models.user import User, UserStatus
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

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
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user for session tests."""
    from app.core.security import hash_password
    return UserRepository.create(
        db=db_session,
        email="sessionuser@example.com",
        username="sessionuser",
        hashed_password=hash_password("sessionpass123"),
        full_name="Session Test User",
        status=UserStatus.ACTIVE,
        is_verified=False,
    )


@pytest.fixture
def generate_refresh_token():
    """Return the generate_refresh_token utility function."""
    from app.core.security import generate_refresh_token
    return generate_refresh_token


# =============================================================================
# Session Model Tests
# =============================================================================

class TestSessionModel:
    """Tests for Session model creation and constraints."""

    def test_create_session(self, db_session, test_user):
        """Test creating a session."""
        expires_at = datetime.now(UTC) + timedelta(days=30)
        session = Session(
            user_id=test_user.id,
            session_token="test_refresh_token_123",
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.session_token == "test_refresh_token_123"
        assert session.status == SessionStatus.ACTIVE
        assert session.is_expired is False

    def test_session_is_expired(self, db_session, test_user):
        """Test session expiration property."""
        # Create an expired session
        expires_at = datetime.now(UTC) - timedelta(days=1)
        session = Session(
            user_id=test_user.id,
            session_token="expired_token",
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
        )
        db_session.add(session)
        db_session.commit()

        assert session.is_expired is True

    def test_unique_session_token_constraint(self, db_session, test_user):
        """Test that session token must be unique."""
        from sqlalchemy import exc

        expires_at = datetime.now(UTC) + timedelta(days=30)
        session1 = Session(
            user_id=test_user.id,
            session_token="unique_token_123",
            expires_at=expires_at,
        )
        db_session.add(session1)
        db_session.commit()

        session2 = Session(
            user_id=test_user.id,
            session_token="unique_token_123",
            expires_at=expires_at,
        )
        db_session.add(session2)

        with pytest.raises(exc.IntegrityError):
            db_session.commit()
        db_session.rollback()


# =============================================================================
# SessionRepository Tests
# =============================================================================

class TestSessionRepository:
    """Tests for SessionRepository operations."""

    def test_create_session(self, db_session, test_user, generate_refresh_token):
        """Test creating a session via repository."""
        token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        session = SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token,
            expires_at=expires_at,
            ip_address="192.168.1.1",
            user_agent="Test Browser",
        )

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.session_token == token
        assert session.status == SessionStatus.ACTIVE
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Test Browser"

    def test_get_by_token(self, db_session, test_user, generate_refresh_token):
        """Test getting session by token."""
        token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token,
            expires_at=expires_at,
        )

        retrieved = SessionRepository.get_by_token(db_session, token)
        assert retrieved is not None
        assert retrieved.session_token == token

    def test_get_by_token_not_found(self, db_session):
        """Test getting non-existent session by token."""
        session = SessionRepository.get_by_token(db_session, "nonexistent-token")
        assert session is None

    def test_get_by_token_expired(self, db_session, test_user):
        """Test that expired sessions are not returned."""
        expires_at = datetime.now(UTC) - timedelta(days=1)

        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token="expired_token",
            expires_at=expires_at,
        )

        session = SessionRepository.get_by_token(db_session, "expired_token")
        assert session is None

    def test_get_by_token_revoked(self, db_session, test_user, generate_refresh_token):
        """Test that revoked sessions are not returned."""
        token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        session = SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token,
            expires_at=expires_at,
        )

        SessionRepository.revoke(db_session, session)

        retrieved = SessionRepository.get_by_token(db_session, token)
        assert retrieved is None

    def test_get_active_by_user(self, db_session, test_user, generate_refresh_token):
        """Test getting active sessions for a user."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token1,
            expires_at=expires_at,
        )
        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token2,
            expires_at=expires_at,
        )

        sessions = SessionRepository.get_active_by_user(db_session, test_user.id)
        assert len(sessions) == 2

    def test_revoke_session(self, db_session, test_user, generate_refresh_token):
        """Test revoking a session."""
        token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        session = SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token,
            expires_at=expires_at,
        )

        assert session.status == SessionStatus.ACTIVE

        revoked = SessionRepository.revoke(db_session, session)
        assert revoked.status == SessionStatus.REVOKED

    def test_revoke_all_by_user(self, db_session, test_user, generate_refresh_token):
        """Test revoking all sessions for a user."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token1,
            expires_at=expires_at,
        )
        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token2,
            expires_at=expires_at,
        )

        count = SessionRepository.revoke_all_by_user(db_session, test_user.id)
        assert count == 2

        # Verify sessions are revoked
        sessions = SessionRepository.get_active_by_user(db_session, test_user.id)
        assert len(sessions) == 0

    def test_revoke_all_except_one(self, db_session, test_user, generate_refresh_token):
        """Test revoking all sessions except one."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        token3 = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        session1 = SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token1,
            expires_at=expires_at,
        )
        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token2,
            expires_at=expires_at,
        )
        SessionRepository.create(
            db=db_session,
            user_id=test_user.id,
            session_token=token3,
            expires_at=expires_at,
        )

        count = SessionRepository.revoke_all_by_user(
            db=db_session,
            user_id=test_user.id,
            except_session_id=session1.id,
        )
        assert count == 2

        # Verify only session1 is still active
        sessions = SessionRepository.get_active_by_user(db_session, test_user.id)
        assert len(sessions) == 1
        assert sessions[0].id == session1.id


# =============================================================================
# Token Generation Tests
# =============================================================================

class TestTokenGeneration:
    """Tests for secure token generation."""

    def test_generate_refresh_token_unique(self, generate_refresh_token):
        """Test that generated tokens are unique."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        assert token1 != token2

    def test_generate_refresh_token_length(self, generate_refresh_token):
        """Test that generated tokens have correct length."""
        token = generate_refresh_token()
        # secrets.token_hex(32) produces 64 hex characters
        assert len(token) == 64

    def test_generate_refresh_token_hex(self, generate_refresh_token):
        """Test that generated tokens are valid hex strings."""
        token = generate_refresh_token()
        # Should be a valid hex string
        int(token, 16)
