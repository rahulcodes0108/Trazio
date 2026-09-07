"""Mapbox services for geocoding, road routing, and travel matrices."""

from __future__ import annotations

from typing import Any, Sequence

import httpx

from app.core.config import settings


MAPBOX_GEOCODING_URL = (
    "https://api.mapbox.com/search/geocode/v6/forward"
)

MAPBOX_DIRECTIONS_URL = (
    "https://api.mapbox.com/directions/v5"
)

MAPBOX_MATRIX_URL = (
    "https://api.mapbox.com/directions-matrix/v1"
)


class MapboxServiceError(Exception):
    """Raised when a Mapbox API operation fails."""


# Map TRAZIO transport modes to Mapbox routing profiles.
#
# Mapbox does not provide a public-transport or mixed profile through
# the Directions/Matrix APIs, so those modes use driving as a practical
# fallback until TRAZIO has a dedicated public-transit routing provider.
MAPBOX_PROFILES = {
    "walking": "mapbox/walking",
    "bicycling": "mapbox/cycling",
    "driving": "mapbox/driving",
    "driving-traffic": "mapbox/driving-traffic",
    "public_transport": "mapbox/driving",
    "mixed": "mapbox/driving",
    "flight": "mapbox/driving",
}


def _require_token() -> str:
    """Return the configured Mapbox token or raise an error."""
    token = settings.MAPBOX_ACCESS_TOKEN

    if not token:
        raise MapboxServiceError(
            "Mapbox access token is not configured."
        )

    return token


def _get_profile(transport_mode: str) -> str:
    """Return the Mapbox routing profile for a TRAZIO transport mode."""
    return MAPBOX_PROFILES.get(
        transport_mode,
        MAPBOX_PROFILES["mixed"],
    )


def _build_coordinate_string(
    coordinates: Sequence[tuple[float, float]],
) -> str:
    """Convert TRAZIO coordinates to Mapbox longitude,latitude format."""
    return ";".join(
        f"{longitude},{latitude}"
        for latitude, longitude in coordinates
    )


def geocode_location(
    location: str,
) -> tuple[float, float]:
    """Convert a human-readable location into latitude/longitude."""
    token = _require_token()

    location = location.strip()

    if not location:
        raise MapboxServiceError(
            "Location cannot be empty."
        )

    params: dict[str, Any] = {
        "q": location,
        "access_token": token,
        "limit": 1,
    }

    try:
        response = httpx.get(
            MAPBOX_GEOCODING_URL,
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MapboxServiceError(
            "Mapbox geocoding request failed."
        ) from exc

    data = response.json()

    features = data.get("features", [])

    if not features:
        raise MapboxServiceError(
            f"Unable to find coordinates for '{location}'."
        )

    coordinates = (
        features[0]
        .get("geometry", {})
        .get("coordinates")
    )

    if not coordinates or len(coordinates) < 2:
        raise MapboxServiceError(
            "Mapbox returned invalid coordinates."
        )

    longitude = float(coordinates[0])
    latitude = float(coordinates[1])

    return latitude, longitude


def get_directions(
    coordinates: list[tuple[float, float]],
    transport_mode: str,
) -> list[dict[str, float]]:
    """Get road distance and duration for each route leg.

    Args:
        coordinates:
            Ordered list of ``(latitude, longitude)`` pairs.
            The first coordinate is the trip starting point.

        transport_mode:
            TRAZIO transport mode such as ``driving``,
            ``walking``, ``bicycling`` or ``mixed``.

    Returns:
        One dictionary per route leg containing:

        {
            "distance_km": float,
            "duration_minutes": float,
        }

    Raises:
        MapboxServiceError:
            If Mapbox cannot calculate the route.
    """
    if len(coordinates) < 2:
        return []

    if len(coordinates) > 25:
        raise MapboxServiceError(
            "Mapbox Directions supports a maximum of 25 coordinates."
        )

    token = _require_token()

    profile = _get_profile(transport_mode)

    # Mapbox expects longitude,latitude.
    coordinate_string = _build_coordinate_string(coordinates)

    url = (
        f"{MAPBOX_DIRECTIONS_URL}/"
        f"{profile}/"
        f"{coordinate_string}"
    )

    params: dict[str, Any] = {
        "access_token": token,
        "overview": "false",
        "steps": "false",
    }

    try:
        response = httpx.get(
            url,
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MapboxServiceError(
            "Mapbox Directions request failed."
        ) from exc

    data = response.json()

    if data.get("code") != "Ok":
        message = data.get(
            "message",
            "Mapbox could not calculate the route.",
        )

        raise MapboxServiceError(message)

    routes = data.get("routes", [])

    if not routes:
        raise MapboxServiceError(
            "Mapbox returned no routes."
        )

    legs = routes[0].get("legs", [])

    if len(legs) != len(coordinates) - 1:
        raise MapboxServiceError(
            "Mapbox returned an unexpected number of route legs."
        )

    return [
        {
            "distance_km": float(
                leg.get("distance", 0.0)
            ) / 1000.0,
            "duration_minutes": float(
                leg.get("duration", 0.0)
            ) / 60.0,
        }
        for leg in legs
    ]


def get_matrix(
    coordinates: Sequence[tuple[float, float]],
    transport_mode: str,
) -> tuple[list[list[int]], list[list[float]]]:
    """Get travel-time and distance matrices from Mapbox Matrix API.

    Args:
        coordinates:
            List of ``(latitude, longitude)`` pairs.

        transport_mode:
            TRAZIO transport mode such as ``driving``,
            ``walking``, ``bicycling`` or ``mixed``.

    Returns:
        A tuple containing:

        ``travel_minutes``
            Square matrix of integer travel durations in minutes.

        ``distance_km``
            Square matrix of road distances in kilometres.

    Raises:
        MapboxServiceError:
            If Mapbox cannot calculate the matrix.
    """
    coordinate_count = len(coordinates)

    if coordinate_count < 2:
        raise MapboxServiceError(
            "At least two coordinates are required."
        )

    if coordinate_count > 25:
        raise MapboxServiceError(
            "Mapbox Matrix supports a maximum of 25 coordinates."
        )

    token = _require_token()

    profile = _get_profile(transport_mode)

    # Mapbox expects longitude,latitude.
    coordinate_string = _build_coordinate_string(
        coordinates
    )

    url = (
        f"{MAPBOX_MATRIX_URL}/"
        f"{profile}/"
        f"{coordinate_string}"
    )

    params: dict[str, Any] = {
        "access_token": token,
        "annotations": "duration,distance",
    }

    try:
        response = httpx.get(
            url,
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MapboxServiceError(
            "Mapbox Matrix request failed."
        ) from exc

    data = response.json()

    if data.get("code") != "Ok":
        message = data.get(
            "message",
            "Mapbox could not calculate the travel matrix.",
        )

        raise MapboxServiceError(message)

    durations = data.get("durations")
    distances = data.get("distances")

    if durations is None or distances is None:
        raise MapboxServiceError(
            "Mapbox Matrix response did not contain "
            "durations and distances."
        )

    if len(durations) != coordinate_count:
        raise MapboxServiceError(
            "Mapbox returned an unexpected duration matrix size."
        )

    if len(distances) != coordinate_count:
        raise MapboxServiceError(
            "Mapbox returned an unexpected distance matrix size."
        )

    for row in durations:
        if len(row) != coordinate_count:
            raise MapboxServiceError(
                "Mapbox returned an invalid duration matrix."
            )

    for row in distances:
        if len(row) != coordinate_count:
            raise MapboxServiceError(
                "Mapbox returned an invalid distance matrix."
            )

    travel_minutes = [
        [
            0
            if value is None
            else int(round(float(value) / 60.0))
            for value in row
        ]
        for row in durations
    ]

    distance_km = [
        [
            0.0
            if value is None
            else float(value) / 1000.0
            for value in row
        ]
        for row in distances
    ]

    return travel_minutes, distance_km
