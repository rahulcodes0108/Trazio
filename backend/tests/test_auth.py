"""Authentication API tests for Trazio."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.user import User, UserStatus
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
    """Create a test user for authentication tests."""
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
def auth_client(db_session):
    """Create a TestClient using the test database session."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

# =============================================================================
# Password Hashing Tests
# =============================================================================

class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password(self, hash_password):
        """Test that password hashing produces a different output each time."""
        hash1 = hash_password("mypassword")
        hash2 = hash_password("mypassword")
        assert hash1 != "mypassword"
        assert hash1 != hash2
        assert len(hash1) > 0

    def test_verify_password(self, hash_password, verify_password):
        """Test that password verification works correctly."""
        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True
        assert verify_password("wrongpassword", hashed) is False


# =============================================================================
# JWT Token Tests
# =============================================================================

class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_and_decode_access_token(self, create_access_token, decode_access_token):
        """Test that access tokens can be created and decoded."""
        user_id = 123
        token = create_access_token(user_id)
        assert token is not None
        assert len(token) > 0

        decoded_user_id = decode_access_token(token)
        assert decoded_user_id == user_id

    def test_decode_invalid_token(self, decode_access_token):
        """Test that invalid tokens return None."""
        assert decode_access_token("invalid-token") is None
        assert decode_access_token("") is None
        assert decode_access_token("a" * 1000) is None


# =============================================================================
# Registration Tests
# =============================================================================

class TestRegistration:
    """Tests for user registration endpoint."""

    def test_register_new_user(self, auth_client, db_session):
        """Test registering a new user."""
        response = auth_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

    def test_register_duplicate_email(self, auth_client, test_user, db_session):
        """Test that duplicate email registration fails."""
        response = auth_client.post(
            "/auth/register",
            json={
                "email": test_user.email,
                "username": "anotheruser",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, auth_client, test_user, db_session):
        """Test that duplicate username registration fails."""
        response = auth_client.post(
            "/auth/register",
            json={
                "email": "another@example.com",
                "username": test_user.username,
                "password": "securepassword123",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_short_password(self, auth_client):
        """Test that short passwords are rejected."""
        response = auth_client.post(
            "/auth/register",
            json={
                "email": "shortpass@example.com",
                "username": "shortpass",
                "password": "short",
            },
        )
        assert response.status_code == 422  # Pydantic validation error


# =============================================================================
# Login Tests
# =============================================================================

class TestLogin:
    """Tests for user login endpoint."""

    def test_login_with_email(self, auth_client, test_user, db_session):
        """Test logging in with email."""
        response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "testpass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_with_username(self, auth_client, test_user, db_session):
        """Test logging in with username."""
        response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.username,
                "password": "testpass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_credentials(self, auth_client, test_user, db_session):
        """Test that invalid credentials fail."""
        response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_user(self, auth_client):
        """Test that logging in as a non-existent user fails."""
        response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": "nonexistent@example.com",
                "password": "anything",
            },
        )
        assert response.status_code == 401


# =============================================================================
# Protected Routes Tests
# =============================================================================

class TestProtectedRoutes:
    """Tests for protected routes requiring authentication."""

    def test_get_current_user_without_token(self, auth_client):
        """Test that /auth/me requires authentication."""
        response = auth_client.get("/auth/me")
        assert response.status_code == 401

    def test_get_current_user_with_valid_token(self, auth_client, test_user, db_session):
        """Test getting current user with valid access token."""
        # First, login to get tokens
        login_response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "testpass123",
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Use the access token to get current user
        response = auth_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    def test_get_current_user_with_invalid_token(self, auth_client):
        """Test that invalid access token is rejected."""
        response = auth_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


# =============================================================================
# Refresh Token Tests
# =============================================================================

class TestRefreshToken:
    """Tests for token refresh endpoint."""

    def test_refresh_token_valid(self, auth_client, test_user, db_session):
        """Test refreshing access token with valid refresh token."""
        # Login to get refresh token
        login_response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "testpass123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        response = auth_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_at" in data
        # Should NOT return refresh_token in refresh response
        assert "refresh_token" not in data

    def test_refresh_token_invalid(self, auth_client):
        """Test that invalid refresh token fails."""
        response = auth_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )
        assert response.status_code == 401


# =============================================================================
# Logout Tests
# =============================================================================

class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_valid_session(self, auth_client, test_user, db_session):
        """Test logging out with valid refresh token."""
        # Login to get refresh token
        login_response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "testpass123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        response = auth_client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["detail"]

        # Verify session is revoked - refresh should now fail
        refresh_response = auth_client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_response.status_code == 401

    def test_logout_invalid_session(self, auth_client):
        """Test that logging out with invalid token fails."""
        response = auth_client.post(
            "/auth/logout",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401

    def test_logout_twice(self, auth_client, test_user, db_session):
        """Test that logging out twice is safe."""
        # Login to get refresh token
        login_response = auth_client.post(
            "/auth/login",
            json={
                "email_or_username": test_user.email,
                "password": "testpass123",
            },
        )
        refresh_token = login_response.json()["refresh_token"]

        # Logout once
        response1 = auth_client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response1.status_code == 200

        # Logout again - should fail
        response2 = auth_client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response2.status_code == 401
