"""Dynamic replanning service for itinerary regeneration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.destination import Destination
from app.models.itinerary import Itinerary, ItineraryStatus
from app.models.itinerary_stop import ItineraryStop
from app.models.trip import Trip
from app.services.itinerary_generator import (
    ItineraryGenerationError,
    _build_generation_pipeline,
    _execute_itinerary_planning,
    _filter_candidates,
)


class ReplanningError(Exception):
    """Raised when itinerary replanning fails due to validation or execution errors."""


@dataclass(frozen=True)
class ReplanningRequest:
    """Request for dynamic itinerary replanning."""

    unavailable_destination_ids: frozenset[int]
    reason: str | None = None

    def __post_init__(self):
        """Normalize destination IDs to frozenset for deep immutability."""
        # Convert set to frozenset if needed, while maintaining frozen dataclass behavior
        if isinstance(self.unavailable_destination_ids, set):
            # Use object.__setattr__ to bypass frozen restriction during __post_init__
            object.__setattr__(self, 'unavailable_destination_ids', frozenset(self.unavailable_destination_ids))


def _validate_replanning_request(
    itinerary: Itinerary,
    request: ReplanningRequest,
) -> None:
    """
    Validate that the replanning request is valid.

    Args:
        itinerary: Source itinerary to replan
        request: Replanning request with unavailable destinations

    Raises:
        ReplanningError: If request is invalid
    """
    # Must have at least one unavailable destination
    if not request.unavailable_destination_ids:
        raise ReplanningError(
            "Replanning request must specify at least one unavailable destination."
        )

    # Source itinerary must have a trip
    if itinerary.trip is None:
        raise ReplanningError(
            "Source itinerary must have an associated trip."
        )

    # Every unavailable destination must be present in the source itinerary's stops
    source_destination_ids = {stop.destination_id for stop in itinerary.stops}

    for destination_id in request.unavailable_destination_ids:
        if destination_id not in source_destination_ids:
            raise ReplanningError(
                f"Destination {destination_id} is not present in source itinerary."
            )


def _get_eligible_destinations(
    db: Session,
    trip: Trip,
    unavailable_destination_ids: frozenset[int],
) -> list[Destination]:
    """
    Load and filter eligible destinations for replanning.

    Args:
        db: Database session
        trip: Trip context
        unavailable_destination_ids: IDs of destinations that became unavailable

    Returns:
        List of eligible destinations for replanning
    """
    # Load all active destinations from the database
    all_destinations = db.query(Destination).filter(Destination.is_active == True).all()

    # Filter using existing hard trip constraints
    candidates = _filter_candidates(all_destinations, trip)

    # Exclude unavailable destinations
    eligible_destinations = [
        destination
        for destination in candidates
        if destination.id not in unavailable_destination_ids
    ]

    return eligible_destinations


def _get_original_destination_ids(itinerary: Itinerary) -> set[int]:
    """Extract destination IDs from the original itinerary stops."""
    return {stop.destination_id for stop in itinerary.stops}


def _find_highest_itinerary_version(db: Session, trip_id: int) -> int:
    """Find the highest existing itinerary version for a trip."""
    latest = (
        db.query(Itinerary)
        .filter(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.version.desc())
        .first()
    )

    return latest.version if latest else 0


def _build_replanning_notes(
    source_version: int,
    unavailable_destination_ids: set[int],
    reason: str | None,
) -> str:
    """Build descriptive notes for the replanned itinerary."""
    unavailable_dests = sorted(unavailable_destination_ids)
    unavailable_str = ", ".join(str(dest_id) for dest_id in unavailable_dests)

    parts = [
        "Replanned itinerary due to destination availability changes.",
        f"Source itinerary version: {source_version}",
        f"Unavailable destination(s): {unavailable_str}",
        "Current destination availability was used.",
        "TRAZIO re-optimized the route.",
    ]

    if reason:
        parts.append(f"Reason: {reason}")

    # Join and truncate to fit in the database field (500 characters)
    notes = " ".join(parts)

    return notes[:500]


def _append_replanning_context_to_reason(
    original_reason: str | None,
    unavailable_destination_ids: set[int],
) -> str:
    """Append replanning context to selection reason."""
    if original_reason:
        base_reason = original_reason.rstrip(".")
    else:
        base_reason = "Selected by the itinerary optimizer under the trip constraints"

    unavailable_dests = sorted(unavailable_destination_ids)
    unavailable_str = ", ".join(str(dest_id) for dest_id in unavailable_dests)

    replanning_context = (
        f" Selected as replacement during replanning because destination(s) "
        f"{unavailable_str} became unavailable."
    )

    # Combine and truncate to fit in the database field (500 characters)
    combined = f"{base_reason}{replanning_context}"

    return combined[:500]


def _create_itinerary_stops(
    db: Session,
    itinerary: Itinerary,
    selected: list[tuple[Destination, int, int, float, str]],
    trip: Trip,
    unavailable_destination_ids: frozenset[int],
    original_destination_ids: set[int],
) -> list[ItineraryStop]:
    """Create itinerary stops for the replanned itinerary."""
    transport_mode = str(
        getattr(trip.transport_mode, "value", trip.transport_mode)
    )
    currency = trip.budget_currency or "INR"

    stops = []
    for sequence, (
        destination,
        travel_duration,
        visit_duration,
        distance_km,
        selection_reason,
    ) in enumerate(selected, start=1):
        # Append replanning context only for genuinely new replacement destinations
        # A destination is a replacement if it's not in the original itinerary
        if destination.id not in original_destination_ids:
            # This is a new replacement destination
            enhanced_reason = _append_replanning_context_to_reason(
                selection_reason, unavailable_destination_ids
            )
        else:
            # This is an unchanged original destination - keep original reason
            enhanced_reason = selection_reason

        stop = ItineraryStop(
            itinerary_id=itinerary.id,
            destination_id=destination.id,
            sequence=sequence,
            visit_duration_minutes=visit_duration,
            estimated_travel_duration_minutes=travel_duration,
            estimated_travel_distance_km=distance_km,
            travel_mode=transport_mode,
            estimated_cost=float(destination.entry_fee or 0.0),
            estimated_cost_currency=currency,
            selection_reason=enhanced_reason,
        )

        stops.append(stop)
        db.add(stop)

    return stops


def replan_itinerary(
    db: Session,
    itinerary: Itinerary,
    request: ReplanningRequest,
) -> Itinerary:
    """
    Create a new itinerary version by replanning around unavailable destinations.

    This function implements dynamic replanning for destination availability changes.

    Steps:
    1. Validate the replanning request
    2. Load the current active destination pool
    3. Filter out unavailable destinations and apply trip constraints
    4. Build the candidate pipeline using existing intelligence functions
    5. Execute the shared planning pipeline
    6. Create new itinerary version with updated stops
    7. Preserve all existing itinerary history

    Args:
        db: Database session
        itinerary: Source itinerary to replan
        request: Replanning request with unavailable destinations and reason

    Returns:
        New itinerary with version N+1

    Raises:
        ReplanningError: If validation fails
        ItineraryGenerationError: If planning execution fails
    """
    # Step 1: Validation
    _validate_replanning_request(itinerary, request)

    trip = itinerary.trip

    if trip is None:
        raise ReplanningError("Source itinerary must have an associated trip.")

    # Step 2: Get original destination IDs
    original_destination_ids = _get_original_destination_ids(itinerary)

    # Step 3: Load and filter eligible destinations
    eligible_destinations = _get_eligible_destinations(
        db=db,
        trip=trip,
        unavailable_destination_ids=request.unavailable_destination_ids,
    )

    if not eligible_destinations:
        raise ReplanningError(
            "No eligible destinations available for replanning."
        )

    # Step 4: Build the generation pipeline (reuses Phase 8A intelligence)
    ranked_candidates, candidate_coordinates = _build_generation_pipeline(
        db=db,
        trip=trip,
        candidates=eligible_destinations,
        user_profile=None,  # Will be built by _rank_candidates_with_intelligence
        start_coordinates=None,  # Will be geocoded by _build_generation_pipeline
    )

    # Step 5: Execute shared planning pipeline (reuses Phase 8B.1)
    start_coordinates = candidate_coordinates[0] if candidate_coordinates else None

    if start_coordinates is None:
        raise ItineraryGenerationError("Unable to determine starting coordinates.")

    selected, total_duration, total_travel_duration, total_cost = (
        _execute_itinerary_planning(
            ranked_candidates=ranked_candidates,
            candidate_coordinates=candidate_coordinates,
            trip=trip,
            start_coordinates=start_coordinates,
        )
    )

    # Step 6: Create new itinerary version
    source_version = itinerary.version
    new_version = _find_highest_itinerary_version(db, trip.id) + 1

    notes = _build_replanning_notes(
        source_version=source_version,
        unavailable_destination_ids=request.unavailable_destination_ids,
        reason=request.reason,
    )

    new_itinerary = Itinerary(
        trip_id=trip.id,
        version=new_version,
        status=ItineraryStatus.GENERATED,
        total_duration_minutes=total_duration,
        estimated_travel_duration_minutes=total_travel_duration,
        estimated_cost=round(total_cost, 2),
        estimated_cost_currency=trip.budget_currency or "INR",
        is_optimized=True,
        notes=notes,
    )

    db.add(new_itinerary)
    db.flush()

    # Step 7: Create itinerary stops with replanning context
    _create_itinerary_stops(
        db=db,
        itinerary=new_itinerary,
        selected=selected,
        trip=trip,
        unavailable_destination_ids=request.unavailable_destination_ids,
        original_destination_ids=original_destination_ids,
    )

    # Ensure the source itinerary remains unchanged
    db.refresh(itinerary)

    db.commit()
    db.refresh(new_itinerary)

    return new_itinerary