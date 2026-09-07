from unittest.mock import Mock, patch

from app.services.mapbox_service import get_matrix


def test_matrix_converts_mapbox_units():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": "Ok",
        "durations": [
            [0, 120, 300],
            [120, 0, 180],
            [300, 180, 0],
        ],
        "distances": [
            [0, 1000, 2500],
            [1000, 0, 1500],
            [2500, 1500, 0],
        ],
    }

    with patch(
        "app.services.mapbox_service.httpx.get",
        return_value=mock_response,
    ):
        minutes, distances = get_matrix(
            [
                (13.0505, 80.2427),
                (13.0520, 80.2425),
                (13.0504, 80.2507),
            ],
            "driving",
        )

    assert minutes == [
        [0, 2, 5],
        [2, 0, 3],
        [5, 3, 0],
    ]

    assert distances == [
        [0.0, 1.0, 2.5],
        [1.0, 0.0, 1.5],
        [2.5, 1.5, 0.0],
    ]


def test_matrix_rejects_more_than_25_coordinates():
    coordinates = [
        (13.0, 80.0)
        for _ in range(26)
    ]

    try:
        get_matrix(coordinates, "driving")
        assert False, "Expected MapboxServiceError"
    except Exception as exc:
        assert "maximum of 25" in str(exc)


def test_matrix_requires_two_coordinates():
    try:
        get_matrix([(13.0, 80.0)], "driving")
        assert False, "Expected MapboxServiceError"
    except Exception as exc:
        assert "At least two" in str(exc)
