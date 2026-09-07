"""Pytest configuration and fixtures for Trazio backend."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(db_session):
    """Create a TestClient using the same database session as the test."""
    from app.db.session import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Authentication Test Fixtures
# =============================================================================

@pytest.fixture
def hash_password():
    """Return the hash_password utility function."""
    from app.core.security import hash_password
    return hash_password


@pytest.fixture
def verify_password():
    """Return the verify_password utility function."""
    from app.core.security import verify_password
    return verify_password


@pytest.fixture
def create_access_token():
    """Return the create_access_token utility function."""
    from app.core.security import create_access_token
    return create_access_token


@pytest.fixture
def decode_access_token():
    """Return the decode_access_token utility function."""
    from app.core.security import decode_access_token
    return decode_access_token


@pytest.fixture
def generate_refresh_token():
    """Return the generate_refresh_token utility function."""
    from app.core.security import generate_refresh_token
    return generate_refresh_token
