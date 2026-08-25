"""Service layer for Trip operations."""

from datetime import date

from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.repositories.trip_repository import TripRepository


class TripService:
    """
    Service layer for Trip operations.

    Establishes clean boundary between API/application logic and
    the TripRepository.
    """

    @staticmethod
    def create_trip(
        db: Session,
        user_id: int,
        title: str,
        start_location: str,
        start_date: date,
        **kwargs,
    ) -> Trip:
        """Create a new trip."""
        return TripRepository.create(
            db=db,
            user_id=user_id,
            title=title,
            start_location=start_location,
            start_date=start_date,
            **kwargs,
        )

    @staticmethod
    def get_trip_by_id(db: Session, trip_id: int) -> Trip | None:
        """Get trip by ID."""
        return TripRepository.get_by_id(db=db, trip_id=trip_id)

    @staticmethod
    def list_trips_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trip]:
        """List trips by user."""
        return TripRepository.list_by_user(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_trip_by_share_token(db: Session, share_token: str) -> Trip | None:
        """Get trip by share token."""
        return TripRepository.get_by_share_token(db=db, share_token=share_token)
