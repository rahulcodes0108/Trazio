"""Service for generating personalized, constraint-aware itineraries."""

from __future__ import annotations

from dataclasses import replace

from datetime import time
from typing import Any
from app.services.crowd_baseline import estimate_crowd_baseline
from app.services.personalization import PersonalizationProfile
from sqlalchemy.orm import Session

from app.models.destination import Destination
from app.models.itinerary import Itinerary, ItineraryStatus
from app.models.itinerary_stop import ItineraryStop
from app.models.trip import BudgetLevel, Trip, TripStatus
from app.models.user import User
from app.services.destination_scorer import DestinationScore, rank_destinations
from app.services.itinerary_optimizer import optimize_itinerary
from app.services.mapbox_service import (
    MapboxServiceError,
    geocode_location,
    get_directions,
    get_matrix,
)
from app.services.personalization import (
    build_user_profile,
    hybrid_personalization_score,
    personalization_explanation,
)
from app.services.weather_context import (
    apply_weather_score,
    get_destination_weather_context,
    WeatherContext,
)
from app.services.route_optimizer import get_coordinates

class ItineraryGenerationError(Exception):
    """Raised when an itinerary cannot be generated."""


DEFAULT_VISIT_DURATION_MINUTES = 60

# Mapbox supports a maximum of 25 coordinates.
# One coordinate is reserved for the trip starting point.
MAX_MAPBOX_DESTINATIONS = 24

# Existing budget-level candidate eligibility rules.
BUDGET_ENTRY_FEE_LIMITS = {
    BudgetLevel.ECONOMY: 500.0,
    BudgetLevel.MID_RANGE: 2000.0,
    BudgetLevel.LUXURY: float("inf"),
    BudgetLevel.CUSTOM: float("inf"),
}


def _destination_fee(destination: Destination) -> float:
    """Return a destination's entry fee."""
    return float(destination.entry_fee or 0.0)


def _filter_candidates(
    destinations: list[Destination],
    trip: Trip,
) -> list[Destination]:
    """
    Filter destinations using hard trip constraints only.

    Preferences are intentionally NOT used here. They are soft
    recommendation signals handled by the personalization layer.
    """

    maximum_fee = BUDGET_ENTRY_FEE_LIMITS.get(
        trip.budget_level,
        float("inf"),
    )

    return [
        destination
        for destination in destinations
        if destination.is_active
        and _destination_fee(destination) <= maximum_fee
    ]


def _transport_mode_value(trip: Trip) -> str:
    """Return the normalized transport mode."""

    return str(
        getattr(
            trip.transport_mode,
            "value",
            trip.transport_mode,
        )
    )


def _visit_duration(destination: Destination) -> int:
    """Return a valid visit duration for a destination."""

    duration = destination.average_visit_duration_minutes

    if duration is None:
        return DEFAULT_VISIT_DURATION_MINUTES

    return max(0, int(duration))


def _budget_amount(trip: Trip) -> float | None:
    """Return the numeric trip budget when one is provided."""

    if trip.budget_amount is None:
        return None

    return max(0.0, float(trip.budget_amount))

DEFAULT_CROWD_VISIT_TIME = time(9, 0)
CROWD_PENALTY_WEIGHT = 0.10


def _crowd_visit_time(trip: Trip) -> time:
    """Return the planning-time used for the MVP crowd baseline."""

    if trip.start_time is not None:
        return trip.start_time

    return DEFAULT_CROWD_VISIT_TIME


def apply_crowd_score(
    destination_score,
    trip: Trip,
    weather_score: float | None = None,
):
    """Apply deterministic crowd pressure as a soft ranking penalty."""

    visit_time = _crowd_visit_time(trip)

    crowd = estimate_crowd_baseline(
        destination=destination_score.destination,
        visit_date=trip.start_date,
        visit_time=visit_time,
        weather_score=weather_score,
    )

    penalty = crowd.score * CROWD_PENALTY_WEIGHT

    total = max(
        0.0,
        destination_score.total_score - penalty,
    )

    explanation = destination_score.explanation.rstrip(".")

    # Strip any trailing period from crowd explanation to avoid double punctuation
    crowd_explanation = crowd.explanation.rstrip(".")

    explanation = (
        f"{explanation}; "
        f"{crowd_explanation}."
    )

    return replace(
        destination_score,
        total_score=round(total, 2),
        explanation=explanation,
    )


def _apply_personalization(
    scored_destination: DestinationScore,
    destination: Destination,
    trip: Trip,
    profile: PersonalizationProfile,
) -> DestinationScore:
    """Apply personalization scoring to a destination score."""
    personalization_score = hybrid_personalization_score(
        destination,
        trip,
        profile,
    )

    personalized_score = round(
        scored_destination.total_score * 0.65
        + personalization_score * 0.35,
        2,
    )

    personalization_reason = personalization_explanation(
        destination,
        trip,
        profile,
    )

    if personalization_reason:
        explanation = (
            f"{scored_destination.explanation} "
            f"{personalization_reason}"
        )
    else:
        explanation = scored_destination.explanation

    return replace(
        scored_destination,
        total_score=personalized_score,
        explanation=explanation,
    )


def _apply_weather_and_crowd(
    scored_destination: DestinationScore,
    destination: Destination,
    trip: Trip,
    weather_context: WeatherContext | None = None,
) -> DestinationScore:
    """Apply weather and crowd intelligence to a destination score.

    This function applies weather and crowd scoring independently of personalization,
    allowing all trips to benefit from these intelligence signals.
    """
    result = scored_destination

    # Apply weather intelligence if available
    if weather_context is not None:
        result = apply_weather_score(
            destination_score=result,
            weather_context=weather_context,
        )

    # Apply crowd intelligence
    weather_score = None
    if weather_context is not None:
        weather_score = weather_context.suitability.score

    result = apply_crowd_score(
        destination_score=result,
        trip=trip,
        weather_score=weather_score,
    )

    return result


def _rank_candidates_with_intelligence(
    db: Session,
    trip: Trip,
    candidates: list[Destination],
    user_profile: PersonalizationProfile | None = None,
) -> list[DestinationScore]:
    """
    Rank destinations using the full intelligence pipeline.

    This is the reusable core ranking function that applies:
    1. Baseline destination scoring
    2. Optional personalization (if user_profile provided)
    3. Weather intelligence (independent of personalization)
    4. Crowd intelligence (independent of personalization)

    Args:
        db: Database session (used for personalization profile building if needed)
        trip: The trip context
        candidates: Filtered list of eligible destinations
        user_profile: Optional pre-built personalization profile

    Returns:
        Ranked list of DestinationScore objects
    """
    # Step 1: Baseline destination scoring
    base_ranked = rank_destinations(
        candidates,
        trip,
    )

    # Step 2: Prepare weather contexts for all destinations
    # This is done for all candidates regardless of personalization
    weather_contexts = {}
    for destination in candidates:
        weather_context = get_destination_weather_context(
            destination=destination,
            forecast_date=trip.start_date,
        )
        weather_contexts[destination.id] = weather_context

    ranked_with_intelligence = []

    for scored_destination in base_ranked:
        destination = scored_destination.destination
        weather_context = weather_contexts.get(destination.id)

        # Step 2: Apply personalization if profile is available
        if user_profile is not None:
            scored_destination = _apply_personalization(
                scored_destination,
                destination,
                trip,
                user_profile,
            )

        # Step 3: Apply weather and crowd intelligence (always applied)
        scored_destination = _apply_weather_and_crowd(
            scored_destination,
            destination,
            trip,
            weather_context,
        )

        ranked_with_intelligence.append(scored_destination)

    # Final ranking
    ranked_with_intelligence.sort(
        key=lambda item: (
            -item.total_score,
            -item.popularity_score,
            item.destination.id,
        )
    )

    return ranked_with_intelligence


def _build_generation_pipeline(
    db: Session,
    trip: Trip,
    candidates: list[Destination],
    user_profile: PersonalizationProfile | None = None,
    start_coordinates: tuple[float, float] | None = None,
) -> tuple[list[DestinationScore], list[tuple[float, float]]]:
    """
    Build the reusable itinerary generation pipeline.

    This function implements the shared pipeline steps that can be reused by both
    normal itinerary generation and future dynamic replanning:

    1. Filter hard-eligible destinations (done by caller)
    2. Rank candidates with intelligence (baseline + personalization + weather + crowd)
    3. Apply Mapbox coordinate limit
    4. Build coordinate sequence with start location

    Args:
        db: Database session
        trip: Trip context
        candidates: Pre-filtered list of eligible destinations
        user_profile: Optional pre-built personalization profile
        start_coordinates: Optional pre-computed start coordinates

    Returns:
        Tuple of (ranked_candidates, candidate_coordinates)

    Raises:
        ItineraryGenerationError: If no candidates or too many coordinates
    """
    # Step 1: Rank candidates with full intelligence pipeline
    ranked_candidates = _rank_candidates_with_intelligence(
        db=db,
        trip=trip,
        candidates=candidates,
        user_profile=user_profile,
    )

    # Step 2: Apply Mapbox coordinate limit
    ranked_candidates = ranked_candidates[:MAX_MAPBOX_DESTINATIONS]

    if not ranked_candidates:
        raise ItineraryGenerationError(
            "No destinations are available for route planning."
        )

    # Step 3: Build coordinate sequence
    if start_coordinates is None:
        try:
            start_coordinates = geocode_location(trip.start_location)
        except MapboxServiceError as exc:
            raise ItineraryGenerationError(
                f"Unable to locate trip starting point "
                f"'{trip.start_location}'."
            ) from exc

    candidate_coordinates: list[tuple[float, float]] = [start_coordinates]

    for scored_destination in ranked_candidates:
        candidate_coordinates.append(
            get_coordinates(scored_destination.destination)
        )

    if len(candidate_coordinates) > 25:
        raise ItineraryGenerationError(
            "Too many coordinates for Mapbox routing."
        )

    return ranked_candidates, candidate_coordinates


def _rank_personalized_candidates(
    db: Session,
    trip: Trip,
    candidates: list[Destination],
) -> list:
    """
    Rank destinations using:

    Phase 5:
        Baseline destination scoring.

    Phase 6:
        Hybrid personalization.

    Phase 7:
        Weather suitability and crowd intelligence.

    Final ranking:
        Baseline + personalization + weather + crowd context.

    Weather is a soft signal only. If weather data is unavailable,
    the destination keeps its previous score.

    NOTE: This function now delegates to _rank_candidates_with_intelligence
    for the actual ranking logic, ensuring that weather and crowd intelligence
    are applied regardless of personalization availability.
    """

    # Build user profile if available
    user_profile = None
    if trip.user_id is not None:
        user = db.get(User, trip.user_id)
        if user is not None:
            user_profile = build_user_profile(db, user)

    # Use the new reusable ranking function
    return _rank_candidates_with_intelligence(
        db=db,
        trip=trip,
        candidates=candidates,
        user_profile=user_profile,
    )

def generate_itinerary(
    db: Session,
    trip: Trip,
    destinations: list[Destination],
) -> Itinerary:
    """
    Generate and persist a personalized, constraint-aware itinerary.

    Pipeline:

    1. Validate the trip.
    2. Filter hard-eligible destinations.
    3. Build the user's personalization profile.
    4. Apply hybrid destination scoring.
    5. Apply weather suitability and crowd intelligence.
    6. Limit the candidate pool to Mapbox's coordinate limit.
    7. Geocode the trip starting location.
    8. Build a Mapbox travel-time/distance matrix.
    9. Optimize destination selection and ordering with OR-Tools.
    10. Verify the optimized route using Mapbox Directions.
    11. Validate final time and cost constraints.
    12. Persist the itinerary and stops.
    """

    if not trip.is_ready_for_planning:
        raise ItineraryGenerationError(
            "Trip is not ready for itinerary generation."
        )

    # ---------------------------------------------------------
    # 1. Filter candidate destinations
    # ---------------------------------------------------------

    candidates = _filter_candidates(
        destinations,
        trip,
    )

    if not candidates:
        raise ItineraryGenerationError(
            "No destinations match the trip requirements."
        )

    # ---------------------------------------------------------
    # 2. Geocode starting location
    # ---------------------------------------------------------

    try:
        start_coordinates = geocode_location(
            trip.start_location,
        )
    except MapboxServiceError as exc:
        raise ItineraryGenerationError(
            f"Unable to locate trip starting point "
            f"'{trip.start_location}'."
        ) from exc

    # ---------------------------------------------------------
    # 3. Personalized destination ranking
    # ---------------------------------------------------------

    ranked_candidates = _rank_personalized_candidates(
        db=db,
        trip=trip,
        candidates=candidates,
    )

    # Mapbox allows at most 25 coordinates.
    # One coordinate is the starting location.
    ranked_candidates = ranked_candidates[
        :MAX_MAPBOX_DESTINATIONS
    ]

    if not ranked_candidates:
        raise ItineraryGenerationError(
            "No destinations are available for route planning."
        )

    # ---------------------------------------------------------
    # 4. Build coordinate sequence
    # ---------------------------------------------------------

    candidate_coordinates: list[tuple[float, float]] = [
        start_coordinates,
    ]

    for scored_destination in ranked_candidates:
        candidate_coordinates.append(
            get_coordinates(
                scored_destination.destination,
            )
        )

    if len(candidate_coordinates) > 25:
        raise ItineraryGenerationError(
            "Too many coordinates for Mapbox routing."
        )

    # ---------------------------------------------------------
    # 5. Get Mapbox travel matrix
    # ---------------------------------------------------------

    transport_mode = _transport_mode_value(trip)

    try:
        travel_matrix, _distance_matrix = get_matrix(
            coordinates=candidate_coordinates,
            transport_mode=transport_mode,
        )
    except MapboxServiceError as exc:
        raise ItineraryGenerationError(
            "Unable to calculate travel times using Mapbox."
        ) from exc

    # ---------------------------------------------------------
    # 6. Prepare optimizer inputs
    # ---------------------------------------------------------

    visit_durations = [
        _visit_duration(
            scored_destination.destination,
        )
        for scored_destination in ranked_candidates
    ]

    entry_fees = [
        _destination_fee(
            scored_destination.destination,
        )
        for scored_destination in ranked_candidates
    ]

    available_minutes = trip.available_duration_minutes

    if available_minutes is None:
        available_minutes = 480

    available_minutes = max(
        0,
        int(available_minutes),
    )

    budget_amount = _budget_amount(trip)

    # ---------------------------------------------------------
    # 7. OR-Tools optimization
    # ---------------------------------------------------------

    optimization_result = optimize_itinerary(
        candidates=ranked_candidates,
        travel_minutes=travel_matrix,
        visit_durations=visit_durations,
        entry_fees=entry_fees,
        available_minutes=available_minutes,
        budget_amount=budget_amount,
        max_stops=min(8, len(ranked_candidates)),
    )

    if not optimization_result.stops:
        raise ItineraryGenerationError(
            "No destinations fit within the available "
            "trip constraints."
        )

    selected_destinations = [
        stop.destination_score.destination
        for stop in optimization_result.stops
    ]

    # ---------------------------------------------------------
    # 8. Verify optimized route with Mapbox Directions
    # ---------------------------------------------------------

    route_coordinates: list[tuple[float, float]] = [
        start_coordinates,
    ]

    for destination in selected_destinations:
        route_coordinates.append(
            get_coordinates(destination)
        )

    if len(route_coordinates) > 25:
        raise ItineraryGenerationError(
            "Optimized route contains too many destinations."
        )

    try:
        route_legs = get_directions(
            coordinates=route_coordinates,
            transport_mode=transport_mode,
        )
    except MapboxServiceError as exc:
        raise ItineraryGenerationError(
            "Unable to verify the optimized route using Mapbox."
        ) from exc

    if len(route_legs) != len(selected_destinations):
        raise ItineraryGenerationError(
            "Mapbox returned incomplete route information."
        )

    # ---------------------------------------------------------
    # 9. Final constraint validation
    # ---------------------------------------------------------

    selected: list[
        tuple[Destination, int, int, float, str]
    ] = []

    total_duration = 0
    total_travel_duration = 0
    total_distance_km = 0.0
    total_cost = 0.0

    score_by_destination_id = {
        scored.destination.id: scored
        for scored in ranked_candidates
    }

    for index, destination in enumerate(
        selected_destinations
    ):
        leg = route_legs[index]

        distance_km = max(
            0.0,
            float(leg["distance_km"]),
        )

        travel_duration = max(
            0,
            int(
                round(
                    float(leg["duration_minutes"])
                )
            ),
        )

        visit_duration = _visit_duration(
            destination,
        )

        destination_cost = _destination_fee(
            destination,
        )

        candidate_duration = (
            travel_duration + visit_duration
        )

        # Mapbox Directions is the final authority for travel time.
        if (
            total_duration + candidate_duration
            > available_minutes
        ):
            break

        # OR-Tools already enforces this budget constraint.
        # Do not silently continue here because doing so could
        # make the subsequent route legs invalid.
        if (
            budget_amount is not None
            and total_cost + destination_cost
            > budget_amount
        ):
            raise ItineraryGenerationError(
                "Generated itinerary exceeds the trip budget "
                "after Mapbox route verification."
            )

        scored_destination = score_by_destination_id.get(
            destination.id
        )

        if scored_destination is None:
            reason = (
                "Selected by the itinerary optimizer "
                "under the trip constraints."
            )
        else:
            reason = scored_destination.explanation

        selected.append(
            (
                destination,
                travel_duration,
                visit_duration,
                distance_km,
                reason,
            )
        )

        total_duration += candidate_duration
        total_travel_duration += travel_duration
        total_distance_km += distance_km
        total_cost += destination_cost

    if not selected:
        raise ItineraryGenerationError(
            "No destinations fit within the available "
            "trip constraints."
        )

    # Final budget validation.
    if (
        budget_amount is not None
        and total_cost > budget_amount
    ):
        raise ItineraryGenerationError(
            "Generated itinerary exceeds the trip budget."
        )

    # ---------------------------------------------------------
    # 10. Create itinerary version
    # ---------------------------------------------------------

    latest = (
        db.query(Itinerary)
        .filter(
            Itinerary.trip_id == trip.id,
        )
        .order_by(
            Itinerary.version.desc(),
        )
        .first()
    )

    version = (
        latest.version + 1
        if latest
        else 1
    )

    itinerary = Itinerary(
        trip_id=trip.id,
        version=version,
        status=ItineraryStatus.GENERATED,
        total_duration_minutes=total_duration,
        estimated_travel_duration_minutes=(
            total_travel_duration
        ),
        estimated_cost=round(total_cost, 2),
        estimated_cost_currency=(
            trip.budget_currency or "INR"
        ),
        is_optimized=True,
       notes=(
    "Generated automatically by TRAZIO "
    "using hybrid personalized destination "
    "scoring, weather suitability intelligence, "
    "OR-Tools constraint optimization, "
    "and Mapbox road routing."),
    )

    db.add(itinerary)
    db.flush()

    # ---------------------------------------------------------
    # 11. Create itinerary stops
    # ---------------------------------------------------------

    for sequence, (
        destination,
        travel_duration,
        visit_duration,
        distance_km,
        selection_reason,
    ) in enumerate(
        selected,
        start=1,
    ):
        stop = ItineraryStop(
            itinerary_id=itinerary.id,
            destination_id=destination.id,
            sequence=sequence,
            visit_duration_minutes=visit_duration,
            estimated_travel_duration_minutes=(
                travel_duration
            ),
            estimated_travel_distance_km=(
                distance_km
            ),
            travel_mode=transport_mode,
            estimated_cost=_destination_fee(
                destination,
            ),
            estimated_cost_currency=(
                trip.budget_currency or "INR"
            ),
            selection_reason=selection_reason,
        )

        db.add(stop)

    trip.status = TripStatus.PLANNING

    db.commit()
    db.refresh(itinerary)

    return itinerary
