"""API router for itinerary endpoints.

Provides endpoints for itinerary management with ownership validation
and automatic itinerary generation.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_current_user
from app.api.schemas import (
    ErrorDetail,
    ItineraryListResponse,
    ItineraryPublic,
    ItineraryStopListResponse,
    ItineraryStopPublic,
)
from app.db.session import get_db
from app.models.destination import Destination
from app.models.itinerary import Itinerary, ItineraryStatus
from app.models.itinerary_stop import ItineraryStop
from app.models.trip import Trip
from app.models.user import User
from app.services.itinerary_generator import (
    ItineraryGenerationError,
    generate_itinerary,
)
from app.services.itinerary_service import ItineraryService
from app.services.trip_service import TripService


router = APIRouter(prefix="/itineraries", tags=["itineraries"])
logger = logging.getLogger(__name__)

def _convert_itinerary_to_response(
    itinerary: Itinerary,
) -> ItineraryPublic:
    """Convert an Itinerary model instance to ItineraryPublic."""
    return ItineraryPublic(
        id=itinerary.id,
        trip_id=itinerary.trip_id,
        version=itinerary.version,
        status=itinerary.status,
        notes=itinerary.notes,
        total_duration_minutes=itinerary.total_duration_minutes,
        estimated_travel_duration_minutes=(
            itinerary.estimated_travel_duration_minutes
        ),
        estimated_cost=itinerary.estimated_cost,
        estimated_cost_currency=itinerary.estimated_cost_currency,
        is_optimized=itinerary.is_optimized,
        stop_count=itinerary.stop_count,
        created_at=itinerary.created_at,
        updated_at=itinerary.updated_at,
    )


def _convert_itinerary_stop_to_response(
    stop: ItineraryStop,
) -> ItineraryStopPublic:
    """Convert an ItineraryStop model instance to ItineraryStopPublic."""
    return ItineraryStopPublic(
        id=stop.id,
        itinerary_id=stop.itinerary_id,
        destination_id=stop.destination_id,
        sequence=stop.sequence,
        planned_arrival=stop.planned_arrival,
        planned_departure=stop.planned_departure,
        visit_duration_minutes=stop.visit_duration_minutes,
        estimated_travel_duration_minutes=(
            stop.estimated_travel_duration_minutes
        ),
        estimated_travel_distance_km=(
            stop.estimated_travel_distance_km
        ),
        travel_mode=stop.travel_mode,
        selection_reason=stop.selection_reason,
        notes=stop.notes,
        estimated_cost=stop.estimated_cost,
        estimated_cost_currency=stop.estimated_cost_currency,
        created_at=stop.created_at,
        updated_at=stop.updated_at,
    )


def _validate_trip_ownership(
    trip: Trip | None,
    current_user: User,
    trip_id: int,
) -> Trip:
    """Validate that the current user owns the trip.

    Raises:
        HTTPException: 404 if trip does not exist.
        HTTPException: 403 if user does not own the trip.
    """
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found",
        )

    if trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You do not have permission to access "
                f"trip with ID {trip_id}"
            ),
        )

    return trip


def _validate_itinerary_ownership(
    itinerary: Itinerary | None,
    current_user: User,
    itinerary_id: int,
    db: DBSession,
) -> Itinerary:
    """Validate ownership of an itinerary through its trip.

    Raises:
        HTTPException: 404 if itinerary does not exist.
        HTTPException: 403 if user does not own the itinerary.
    """
    if itinerary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itinerary_id} not found",
        )

    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=itinerary.trip_id,
    )

    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You do not have permission to access "
                f"itinerary with ID {itinerary_id}"
            ),
        )

    return itinerary


@router.post(
    "/trips/{trip_id}",
    response_model=ItineraryPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create an itinerary for a trip",
    description=(
        "Create the next empty itinerary version for a trip "
        "owned by the authenticated user."
    ),
    responses={
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - not the trip owner",
        },
        404: {
            "model": ErrorDetail,
            "description": "Trip not found",
        },
    },
)
async def create_itinerary_for_trip(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ItineraryPublic:
    """Create the next empty itinerary version for an owned trip."""
    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=trip_id,
    )

    _validate_trip_ownership(
        trip,
        current_user,
        trip_id,
    )

    latest = ItineraryService.get_latest_itinerary_by_trip(
        db=db,
        trip_id=trip_id,
    )

    next_version = 1 if latest is None else latest.version + 1

    itinerary = ItineraryService.create_itinerary(
        db=db,
        trip_id=trip_id,
        version=next_version,
        status=ItineraryStatus.DRAFT,
    )

    return _convert_itinerary_to_response(itinerary)


@router.post(
    "/trips/{trip_id}/generate",
    response_model=ItineraryPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an itinerary for a trip",
    description=(
        "Generate an itinerary using trip preferences, budget, "
        "available duration, destination popularity, and route proximity."
    ),
    responses={
        400: {
            "model": ErrorDetail,
            "description": (
                "Trip is not ready for planning or no destinations "
                "fit the trip requirements."
            ),
        },
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - not the trip owner",
        },
        404: {
            "model": ErrorDetail,
            "description": "Trip not found",
        },
        500: {
            "model": ErrorDetail,
            "description": "Internal itinerary generation error",
        },
    },
)
async def generate_itinerary_for_trip(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ItineraryPublic:
    """Generate and persist an itinerary for an owned trip."""

    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=trip_id,
    )

    _validate_trip_ownership(
        trip,
        current_user,
        trip_id,
    )

    destinations = (
        db.query(Destination)
        .filter(Destination.is_active.is_(True))
        .all()
    )

    if not destinations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active destinations are available for itinerary generation.",
        )

    try:
        itinerary = generate_itinerary(
            db=db,
            trip=trip,
            destinations=destinations,
        )
    except ItineraryGenerationError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        logger.exception("Unexpected error generating itinerary for trip %s", trip_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate itinerary.",
        ) from None

    return _convert_itinerary_to_response(itinerary)


@router.get(
    "/trips/{trip_id}",
    response_model=ItineraryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List itineraries by trip",
    description=(
        "Retrieve all itineraries for a specific trip owned "
        "by the authenticated user."
    ),
    responses={
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - not the trip owner",
        },
        404: {
            "model": ErrorDetail,
            "description": "Trip not found",
        },
    },
)
async def list_itineraries_by_trip(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of items to skip",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return",
    ),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ItineraryListResponse:
    """List all itineraries for a specific trip."""

    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=trip_id,
    )

    _validate_trip_ownership(
        trip,
        current_user,
        trip_id,
    )

    itineraries = ItineraryService.list_itineraries_by_trip(
        db=db,
        trip_id=trip_id,
        skip=skip,
        limit=limit,
    )

    itinerary_responses = [
        _convert_itinerary_to_response(itinerary)
        for itinerary in itineraries
    ]

    return ItineraryListResponse(
        itineraries=itinerary_responses,
        count=len(itinerary_responses),
    )


@router.get(
    "/{itinerary_id}",
    response_model=ItineraryPublic,
    status_code=status.HTTP_200_OK,
    summary="Get itinerary by ID",
    description=(
        "Retrieve a specific itinerary by its unique identifier."
    ),
    responses={
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - not the itinerary owner",
        },
        404: {
            "model": ErrorDetail,
            "description": "Itinerary not found",
        },
    },
)
async def get_itinerary_by_id(
    itinerary_id: int = Path(
        ...,
        ge=1,
        description="Itinerary ID",
    ),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ItineraryPublic:
    """Get an itinerary by ID."""

    itinerary = ItineraryService.get_itinerary_by_id(
        db=db,
        itinerary_id=itinerary_id,
    )

    if itinerary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itinerary_id} not found",
        )

    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=itinerary.trip_id,
    )

    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You do not have permission to access "
                f"itinerary with ID {itinerary_id}"
            ),
        )

    return _convert_itinerary_to_response(itinerary)


@router.get(
    "/{itinerary_id}/stops",
    response_model=ItineraryStopListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get itinerary stops",
    description=(
        "Retrieve all stops for a specific itinerary owned "
        "by the authenticated user."
    ),
    responses={
        403: {
            "model": ErrorDetail,
            "description": "Forbidden - not the itinerary owner",
        },
        404: {
            "model": ErrorDetail,
            "description": "Itinerary not found",
        },
    },
)
async def get_itinerary_stops(
    itinerary_id: int = Path(
        ...,
        ge=1,
        description="Itinerary ID",
    ),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ItineraryStopListResponse:
    """Get all stops for an itinerary."""

    itinerary = ItineraryService.get_itinerary_by_id(
        db=db,
        itinerary_id=itinerary_id,
    )

    if itinerary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Itinerary with ID {itinerary_id} not found",
        )

    trip = TripService.get_trip_by_id(
        db=db,
        trip_id=itinerary.trip_id,
    )

    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You do not have permission to access "
                f"itinerary with ID {itinerary_id}"
            ),
        )

    stops = ItineraryService.list_itinerary_stops(
        db=db,
        itinerary_id=itinerary_id,
    )

    stop_responses = [
        _convert_itinerary_stop_to_response(stop)
        for stop in stops
    ]

    return ItineraryStopListResponse(
        stops=stop_responses,
        count=len(stop_responses),
    )
