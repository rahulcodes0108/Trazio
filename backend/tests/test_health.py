"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Test that the health endpoint returns a successful response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_endpoint_response_structure(client: TestClient):
    """Test that the health endpoint returns the expected response structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert "version" in data
