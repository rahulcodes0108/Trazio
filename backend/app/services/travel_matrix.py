"""Travel-time and distance matrix utilities."""

from __future__ import annotations

from typing import Sequence

from app.services.mapbox_service import MapboxService


class TravelMatrixError(Exception):
    """Raised when a travel matrix cannot be generated."""


def build_travel_matrix(
    coordinates: Sequence[tuple[float, float]],
    transport_mode: str,
) -> tuple[list[list[int]], list[list[float]]]:
    """
    Build travel-time and distance matrices.

    coordinates use:
        (latitude, longitude)

    Returns:
        travel_minutes
        distance_km

    Mapbox Directions supports up to 25 coordinates, so the
    current Phase 5 candidate pool must remain within that limit.
    """

    count = len(coordinates)

    if count == 0:
        return [], []

    if count > 25:
        raise TravelMatrixError(
            "Travel matrix cannot contain more than 25 coordinates."
        )

    if count == 1:
        return [[0]], [[0.0]]

    service = MapboxService()

    travel_matrix = [[0 for _ in range(count)] for _ in range(count)]
    distance_matrix = [[0.0 for _ in range(count)] for _ in range(count)]

    for origin_index in range(count):
        remaining = [
            coordinates[index]
            for index in range(count)
            if index != origin_index
        ]

        if not remaining:
            continue

        origin = coordinates[origin_index]

        route_coordinates = [origin, *remaining]

        legs = service.get_directions(
            route_coordinates,
            transport_mode,
        )

        leg_index = 0

        for destination_index in range(count):
            if destination_index == origin_index:
                continue

            if leg_index >= len(legs):
                raise TravelMatrixError(
                    "Mapbox returned an incomplete route matrix."
                )

            leg = legs[leg_index]

            travel_matrix[origin_index][destination_index] = max(
                0,
                int(round(leg["duration_minutes"])),
            )

            distance_matrix[origin_index][destination_index] = max(
                0.0,
                float(leg["distance_km"]),
            )

            leg_index += 1

    return travel_matrix, distance_matrix
