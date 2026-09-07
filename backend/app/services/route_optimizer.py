"""Route optimization utilities for itinerary generation."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Sequence

from geoalchemy2.shape import to_shape

from app.models.destination import Destination


def haversine_distance_km(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """Calculate great-circle distance between two coordinates in kilometres."""
    earth_radius_km = 6371.0

    lat1 = radians(latitude1)
    lat2 = radians(latitude2)

    delta_lat = radians(latitude2 - latitude1)
    delta_lon = radians(longitude2 - longitude1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    return earth_radius_km * 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )


def get_coordinates(
    destination: Destination,
) -> tuple[float, float]:
    """Extract latitude and longitude from a destination location.

    Supports both:
    - PostGIS/GeoAlchemy2 WKBElement values returned from the database.
    - WKT strings such as ``POINT(80.2824 13.0500)`` used in tests.

    Returns:
        A tuple of ``(latitude, longitude)``.
    """
    location = destination.location

    if location is None:
        raise ValueError(
            f"Destination {destination.id}: {destination.name} "
            "does not have a location."
        )

    # Production/database value.
    # GeoAlchemy2 normally returns PostGIS geometry as WKBElement.
    if not isinstance(location, str):
        try:
            point = to_shape(location)

            return float(point.y), float(point.x)

        except Exception as exc:
            raise ValueError(
                f"Unable to extract coordinates for destination "
                f"{destination.id}: {destination.name}"
            ) from exc

    # Test/manual value:
    # POINT(longitude latitude)
    value = location.strip()

    if value.upper().startswith("POINT(") and value.endswith(")"):
        try:
            coordinates = value[6:-1].strip().split()

            if len(coordinates) != 2:
                raise ValueError(
                    "POINT must contain exactly two coordinates."
                )

            longitude = float(coordinates[0])
            latitude = float(coordinates[1])

            return latitude, longitude

        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Unable to extract coordinates for destination "
                f"{destination.id}: {destination.name}"
            ) from exc

    raise ValueError(
        f"Unable to extract coordinates for destination "
        f"{destination.id}: {destination.name}"
    )


def optimize_route(
    destinations: Sequence[Destination],
    start_coordinates: tuple[float, float] | None = None,
) -> list[Destination]:
    """Order destinations using a nearest-neighbour heuristic.

    If ``start_coordinates`` are provided, the first destination is selected
    based on geographic proximity to the trip starting point.

    If ``start_coordinates`` are not provided, the highest-popularity
    destination is selected as the starting point.

    After the first destination, each subsequent destination is selected
    based on the shortest geographic distance from the previously selected
    destination.

    Args:
        destinations:
            Candidate destinations.
        start_coordinates:
            Optional ``(latitude, longitude)`` for the trip starting location.

    Returns:
        Destinations ordered for the itinerary.
    """
    if not destinations:
        return []

    remaining = list(destinations)

    # V2: start from the destination closest to the user's
    # geocoded starting location.
    if start_coordinates is not None:
        start_latitude, start_longitude = start_coordinates

        current = min(
            remaining,
            key=lambda destination: haversine_distance_km(
                start_latitude,
                start_longitude,
                *get_coordinates(destination),
            ),
        )

    # V1 fallback: preserve the existing popularity-based behavior.
    else:
        current = max(
            remaining,
            key=lambda destination: destination.popularity_score,
        )

    route = [current]
    remaining.remove(current)

    # Nearest-neighbour routing for the remaining destinations.
    while remaining:
        current_latitude, current_longitude = get_coordinates(current)

        next_destination = min(
            remaining,
            key=lambda destination: haversine_distance_km(
                current_latitude,
                current_longitude,
                *get_coordinates(destination),
            ),
        )

        route.append(next_destination)
        remaining.remove(next_destination)

        current = next_destination

    return route
