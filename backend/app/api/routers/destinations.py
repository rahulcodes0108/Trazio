"""Destination API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import DestinationListResponse, DestinationPublic
from app.db.session import get_db
from app.models.destination import Destination


router = APIRouter(
    prefix="/destinations",
    tags=["destinations"],
)


def _destination_public(
    destination: Destination,
    location: str,
) -> DestinationPublic:
    """Convert a destination model into its public API representation."""

    return DestinationPublic(
        id=destination.id,
        name=destination.name,
        slug=destination.slug,
        description=destination.description,
        image_url=destination.image_url,
        category=destination.category,
        location=location,
        address_line1=destination.address_line1,
        address_line2=destination.address_line2,
        city=destination.city,
        state_province=destination.state_province,
        postal_code=destination.postal_code,
        country=destination.country,
        opening_hours=destination.opening_hours,
        entry_fee=destination.entry_fee,
        entry_fee_currency=destination.entry_fee_currency,
        average_visit_duration_minutes=(
            destination.average_visit_duration_minutes
        ),
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
    "",
    response_model=DestinationListResponse,
    status_code=status.HTTP_200_OK,
)
def list_destinations(
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of destinations to skip.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of destinations to return.",
    ),
    db: Session = Depends(get_db),
) -> DestinationListResponse:
    """Return a paginated list of active destinations."""

    count_query = select(func.count(Destination.id)).where(
        Destination.is_active.is_(True)
    )

    destinations_query = (
        select(
            Destination,
            func.ST_AsText(Destination.location).label("location_wkt"),
        )
        .where(Destination.is_active.is_(True))
        .order_by(Destination.id)
        .offset(skip)
        .limit(limit)
    )

    total_count = db.scalar(count_query) or 0
    rows = db.execute(destinations_query).all()

    return DestinationListResponse(
        destinations=[
            _destination_public(
                destination=destination,
                location=location_wkt,
            )
            for destination, location_wkt in rows
        ],
        count=total_count,
    )


@router.get(
    "/{destination_id}",
    response_model=DestinationPublic,
    status_code=status.HTTP_200_OK,
)
def get_destination(
    destination_id: int,
    db: Session = Depends(get_db),
) -> DestinationPublic:
    """Return an active destination by ID."""

    row = db.execute(
        select(
            Destination,
            func.ST_AsText(Destination.location).label("location_wkt"),
        ).where(
            Destination.id == destination_id,
            Destination.is_active.is_(True),
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found.",
        )

    destination, location_wkt = row

    return _destination_public(
        destination=destination,
        location=location_wkt,
    )


@router.get(
    "/slug/{slug}",
    response_model=DestinationPublic,
    status_code=status.HTTP_200_OK,
)
def get_destination_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> DestinationPublic:
    """Return an active destination by slug."""

    row = db.execute(
        select(
            Destination,
            func.ST_AsText(Destination.location).label("location_wkt"),
        ).where(
            Destination.slug == slug,
            Destination.is_active.is_(True),
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found.",
        )

    destination, location_wkt = row

    return _destination_public(
        destination=destination,
        location=location_wkt,
    )