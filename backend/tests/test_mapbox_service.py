"""Tests for Mapbox services."""

from unittest.mock import Mock, patch

import pytest

from app.services.mapbox_service import (
    MapboxServiceError,
    geocode_location,
)


def test_geocode_location_returns_latitude_longitude():
    """Geocoding should return latitude and longitude."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "features": [
            {
                "geometry": {
                    "coordinates": [80.2707, 13.0827],
                }
            }
        ]
    }

    with patch(
        "app.services.mapbox_service.httpx.get",
        return_value=mock_response,
    ):
        latitude, longitude = geocode_location("Chennai")

    assert latitude == pytest.approx(13.0827)
    assert longitude == pytest.approx(80.2707)


def test_geocode_location_rejects_empty_location():
    """Empty locations should be rejected."""
    with pytest.raises(MapboxServiceError, match="cannot be empty"):
        geocode_location("   ")


def test_geocode_location_raises_when_no_results():
    """Missing Mapbox results should raise a service error."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "features": []
    }

    with patch(
        "app.services.mapbox_service.httpx.get",
        return_value=mock_response,
    ):
        with pytest.raises(
            MapboxServiceError,
            match="Unable to find coordinates",
        ):
            geocode_location("SomewhereThatDoesNotExist")
