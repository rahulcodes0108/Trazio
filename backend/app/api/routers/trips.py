"""API router for trip endpoints.

Provides endpoints for trip management with ownership validation.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_current_user
from app.api.schemas import (
    ErrorDetail,
    Message,
    TripCreate,
    TripListResponse,
    TripPublic,
    TripUpdate,
)
from app.db.session import get_db
from app.models.trip import Trip
from app.models.user import User
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


def _convert_trip_to_response(trip: Trip) -> TripPublic:
    """Convert a Trip model instance to TripPublic response schema."""
    return TripPublic(
        id=trip.id,
        user_id=trip.user_id,
        title=trip.title,
        description=trip.description,
        start_location=trip.start_location,
        start_date=trip.start_date,
        start_time=trip.start_time,
        end_date=trip.end_date,
        end_time=trip.end_time,
        available_duration_minutes=trip.available_duration_minutes,
        budget_level=trip.budget_level,
        budget_amount=trip.budget_amount,
        budget_currency=trip.budget_currency,
        transport_mode=trip.transport_mode,
        preferences=trip.preferences,
        status=trip.status,
        is_public=trip.is_public,
        share_token=trip.share_token,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


def _validate_trip_ownership(trip: Trip | None, current_user: User, trip_id: int) -> Trip:
    """Validate that the current user owns the trip.

    Raises HTTPException 404 if trip not found, 403 if ownership mismatch.
    """
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip with ID {trip_id} not found",
        )

    if trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to access trip with ID {trip_id}",
        )

    return trip


@router.post(
    "",
    response_model=TripPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trip",
    description="Create a new trip for the authenticated user.",
)
async def create_trip(
    trip_data: TripCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> TripPublic:
    """Create a new trip for the current user.

    The trip will be associated with the authenticated user.
    """
    try:
        trip = TripService.create_trip(
            db=db,
            user_id=current_user.id,
            title=trip_data.title,
            start_location=trip_data.start_location,
            start_date=trip_data.start_date,
            start_time=trip_data.start_time,
            end_date=trip_data.end_date,
            end_time=trip_data.end_time,
            available_duration_minutes=trip_data.available_duration_minutes,
            budget_level=trip_data.budget_level,
            budget_amount=trip_data.budget_amount,
            budget_currency=trip_data.budget_currency,
            transport_mode=trip_data.transport_mode,
            preferences=trip_data.preferences,
            status=trip_data.status,
            is_public=trip_data.is_public,
            share_token=trip_data.share_token,
            description=trip_data.description,
        )

        return _convert_trip_to_response(trip)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create trip: {str(e)}",
        )


@router.get(
    "",
    response_model=TripListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user's trips",
    description="Retrieve all trips for the authenticated user.",
)
async def list_trips(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> TripListResponse:
    """List all trips for the current user with pagination.

    Only returns trips owned by the authenticated user.
    """
    trips = TripService.list_trips_by_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    trip_responses = [_convert_trip_to_response(trip) for trip in trips]

    return TripListResponse(
        trips=trip_responses,
        count=len(trip_responses),
    )


@router.get(
    "/{trip_id}",
    response_model=TripPublic,
    status_code=status.HTTP_200_OK,
    summary="Get trip by ID",
    description="Retrieve a specific trip by its unique identifier.",
    responses={
        403: {"model": ErrorDetail, "description": "Forbidden - not the trip owner"},
        404: {"model": ErrorDetail, "description": "Trip not found"},
    },
)
async def get_trip_by_id(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> TripPublic:
    """Get a trip by its ID.

    Validates that the authenticated user owns the trip.
    """
    trip = TripService.get_trip_by_id(db=db, trip_id=trip_id)
    _validate_trip_ownership(trip, current_user, trip_id)

    return _convert_trip_to_response(trip)


@router.patch(
    "/{trip_id}",
    response_model=TripPublic,
    status_code=status.HTTP_200_OK,
    summary="Update trip",
    description="Update an existing trip owned by the authenticated user.",
    responses={
        403: {"model": ErrorDetail, "description": "Forbidden - not the trip owner"},
        404: {"model": ErrorDetail, "description": "Trip not found"},
    },
)
async def update_trip(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    trip_data: TripUpdate = ...,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> TripPublic:
    """Update a trip by its ID.

    Only allows updating trips owned by the authenticated user.
    """
    trip = TripService.get_trip_by_id(db=db, trip_id=trip_id)
    _validate_trip_ownership(trip, current_user, trip_id)

    # Prepare update data - only include non-None values
    update_data = trip_data.model_dump(exclude_unset=True)

    # Convert date strings to date objects if they exist in update_data
    if 'start_date' in update_data and isinstance(update_data['start_date'], str):
        update_data['start_date'] = date.fromisoformat(update_data['start_date'])
    if 'end_date' in update_data and isinstance(update_data['end_date'], str):
        update_data['end_date'] = date.fromisoformat(update_data['end_date'])

    # Update the trip
    updated_trip = TripService.update(db=db, trip=trip, **update_data)

    return _convert_trip_to_response(updated_trip)


@router.delete(
    "/{trip_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete trip",
    description="Delete a trip owned by the authenticated user.",
    responses={
        403: {"model": ErrorDetail, "description": "Forbidden - not the trip owner"},
        404: {"model": ErrorDetail, "description": "Trip not found"},
    },
)
async def delete_trip(
    trip_id: int = Path(..., ge=1, description="Trip ID"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> Message:
    """Delete a trip by its ID.

    Only allows deleting trips owned by the authenticated user.
    """
    trip = TripService.get_trip_by_id(db=db, trip_id=trip_id)
    _validate_trip_ownership(trip, current_user, trip_id)

    TripService.delete(db=db, trip=trip)

    return Message(detail=f"Trip with ID {trip_id} deleted successfully")
