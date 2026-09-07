from unittest.mock import Mock, patch

import pytest

from app.services.mapbox_service import (
    MapboxServiceError,
    get_directions,
)


@patch("app.services.mapbox_service.httpx.get")
def test_get_directions_returns_route_legs(mock_get):
    response = Mock()

    response.raise_for_status.return_value = None
    response.json.return_value = {
        "code": "Ok",
        "routes": [
            {
                "distance": 2500,
                "duration": 600,
                "legs": [
                    {
                        "distance": 1000,
                        "duration": 240,
                    },
                    {
                        "distance": 1500,
                        "duration": 360,
                    },
                ],
            }
        ],
    }

    mock_get.return_value = response

    with patch(
        "app.services.mapbox_service.settings.MAPBOX_ACCESS_TOKEN",
        "pk.test-token",
    ):
        result = get_directions(
            coordinates=[
                (13.05, 80.24),
                (13.06, 80.25),
                (13.07, 80.26),
            ],
            transport_mode="driving",
        )

    assert len(result) == 2

    assert result[0]["distance_km"] == pytest.approx(1.0)
    assert result[0]["duration_minutes"] == pytest.approx(4.0)

    assert result[1]["distance_km"] == pytest.approx(1.5)
    assert result[1]["duration_minutes"] == pytest.approx(6.0)


def test_get_directions_with_less_than_two_coordinates():
    result = get_directions(
        coordinates=[
            (13.05, 80.24),
        ],
        transport_mode="driving",
    )

    assert result == []


def test_get_directions_rejects_more_than_25_coordinates():
    coordinates = [
        (13.05, 80.24)
        for _ in range(26)
    ]

    with pytest.raises(MapboxServiceError):
        get_directions(
            coordinates=coordinates,
            transport_mode="driving",
        )
