"""Repository for Trip database operations."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trip import Trip, TripStatus


class TripRepository:
    """
    Repository for Trip database operations.

    Provides clean abstraction for Trip CRUD operations.
    """

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        title: str,
        start_location: str,
        start_date: date,
        **kwargs,
    ) -> Trip:
        """
        Create a new trip.

        Args:
            db: SQLAlchemy session
            user_id: Owner user ID
            title: Trip title
            start_location: Starting location
            start_date: Start date
            **kwargs: Additional trip attributes

        Returns:
            Created Trip instance
        """
        trip = Trip(
            user_id=user_id,
            title=title,
            start_location=start_location,
            start_date=start_date,
            **kwargs,
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)
        return trip

    @staticmethod
    def get_by_id(db: Session, trip_id: int) -> Trip | None:
        """Get trip by ID."""
        return db.get(Trip, trip_id)

    @staticmethod
    def list_by_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trip]:
        """List trips by user with pagination."""
        stmt = (
            select(Trip)
            .where(Trip.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(Trip.created_at.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_by_status(
        db: Session,
        status: TripStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trip]:
        """List trips by status with pagination."""
        stmt = (
            select(Trip)
            .where(Trip.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_by_share_token(db: Session, share_token: str) -> Trip | None:
        """Get trip by share token."""
        stmt = select(Trip).where(Trip.share_token == share_token)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def update(db: Session, trip: Trip, **kwargs) -> Trip:
        """Update trip attributes."""
        for key, value in kwargs.items():
            setattr(trip, key, value)
        db.commit()
        db.refresh(trip)
        return trip

    @staticmethod
    def delete(db: Session, trip: Trip) -> None:
        """Delete a trip."""
        db.delete(trip)
        db.commit()
