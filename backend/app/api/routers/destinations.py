"""API router for destination endpoints.

Provides endpoints for retrieving destination information.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, Integer, String, Text, text
from sqlalchemy.orm import Session as DBSession

from app.api.schemas import (
    DestinationListResponse,
    DestinationPublic,
    ErrorDetail,
)
from app.db.session import get_db
from app.models.destination import Destination, DestinationCategory
from app.services.destination_service import DestinationService

router = APIRouter(prefix="/destinations", tags=["destinations"])


def _location_to_wkt(db: DBSession, destination_id: int) -> str:
    result = db.execute(
        text("SELECT ST_AsText(location) FROM destinations WHERE id = :id"),
        {"id": destination_id},
    ).scalar_one()
    return result

@router.get(
    "",
    response_model=DestinationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all destinations",
    description="Retrieve a list of all active destinations with optional pagination.",
)
async def list_destinations(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of items to return"),
    db: DBSession = Depends(get_db),
) -> DestinationListResponse:
    """List all active destinations with pagination.

    Returns a paginated list of active destinations, ordered by creation date.
    """
    destinations = DestinationService.list_destinations(
        db=db,
        skip=skip,
        limit=limit,
    )

    # Convert to response format
    destination_responses = []
    for dest in destinations:
        destination_responses.append(DestinationPublic(
            id=dest.id,
            name=dest.name,
            slug=dest.slug,
            description=dest.description,
            category=DestinationCategory(dest.category),
            location=_location_to_wkt(db, dest.id),
            address_line1=dest.address_line1,
            address_line2=dest.address_line2,
            city=dest.city,
            state_province=dest.state_province,
            postal_code=dest.postal_code,
            country=dest.country,
            opening_hours=dest.opening_hours,
            entry_fee=dest.entry_fee,
            entry_fee_currency=dest.entry_fee_currency,
            average_visit_duration_minutes=dest.average_visit_duration_minutes,
            accessibility=dest.accessibility,
            accessibility_notes=dest.accessibility_notes,
            popularity_score=dest.popularity_score,
            is_active=dest.is_active,
            website_url=dest.website_url,
            phone_number=dest.phone_number,
            email=dest.email,
            created_at=dest.created_at,
            updated_at=dest.updated_at,
        ))

    return DestinationListResponse(
        destinations=destination_responses,
        count=len(destination_responses),
    )


@router.get(
    "/{destination_id}",
    response_model=DestinationPublic,
    status_code=status.HTTP_200_OK,
    summary="Get destination by ID",
    description="Retrieve a specific destination by its unique identifier.",
    responses={
        404: {"model": ErrorDetail, "description": "Destination not found"},
    },
)
async def get_destination_by_id(
    destination_id: int = Path(..., ge=1, description="Destination ID"),
    db: DBSession = Depends(get_db),
) -> DestinationPublic:
    """Get a destination by its ID.

    Returns the destination details or 404 if not found.
    """
    destination = DestinationService.get_destination_by_id(
        db=db,
        destination_id=destination_id,
    )

    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with ID {destination_id} not found",
        )

    return DestinationPublic(
        id=destination.id,
        name=destination.name,
        slug=destination.slug,
        description=destination.description,
        category=DestinationCategory(destination.category),
        location=_location_to_wkt(db, destination.id),
        address_line1=destination.address_line1,
        address_line2=destination.address_line2,
        city=destination.city,
        state_province=destination.state_province,
        postal_code=destination.postal_code,
        country=destination.country,
        opening_hours=destination.opening_hours,
        entry_fee=destination.entry_fee,
        entry_fee_currency=destination.entry_fee_currency,
        average_visit_duration_minutes=destination.average_visit_duration_minutes,
        accessibility=destination.accessibility,
        accessibility_notes=destination.accessibility_notes,
        popularity_score=destination.popularity_score,
        is_active=destination.is_active,
        website_url=destination.website_url,
        phone_number=destination.phone_number,
        email=destination.email,
        created_at=destination.created_at,
        updated_at=destination.updated_at,
    )


@router.get(
    "/slug/{slug}",
    response_model=DestinationPublic,
    status_code=status.HTTP_200_OK,
    summary="Get destination by slug",
    description="Retrieve a specific destination by its unique slug.",
    responses={
        404: {"model": ErrorDetail, "description": "Destination not found"},
    },
)
async def get_destination_by_slug(
    slug: str = Path(..., min_length=1, max_length=120, description="Destination slug"),
    db: DBSession = Depends(get_db),
) -> DestinationPublic:
    """Get a destination by its slug.

    Returns the destination details or 404 if not found.
    """
    destination = DestinationService.get_destination_by_slug(
        db=db,
        slug=slug,
    )

    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with slug '{slug}' not found",
        )

    return DestinationPublic(
        id=destination.id,
        name=destination.name,
        slug=destination.slug,
        description=destination.description,
        category=DestinationCategory(destination.category),
        location=_location_to_wkt(db, destination.id),
        address_line1=destination.address_line1,
        address_line2=destination.address_line2,
        city=destination.city,
        state_province=destination.state_province,
        postal_code=destination.postal_code,
        country=destination.country,
        opening_hours=destination.opening_hours,
        entry_fee=destination.entry_fee,
        entry_fee_currency=destination.entry_fee_currency,
        average_visit_duration_minutes=destination.average_visit_duration_minutes,
        accessibility=destination.accessibility,
        accessibility_notes=destination.accessibility_notes,
        popularity_score=destination.popularity_score,
        is_active=destination.is_active,
        website_url=destination.website_url,
        phone_number=destination.phone_number,
        email=destination.email,
        created_at=destination.created_at,
        updated_at=destination.updated_at,
    )
