"""Repository for Itinerary database operations."""

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.itinerary import Itinerary
from app.models.itinerary_stop import ItineraryStop


class ItineraryRepository:
    """
    Repository for Itinerary database operations.

    Provides clean abstraction for Itinerary CRUD operations
    with version handling.
    """

    @staticmethod
    def create(
        db: Session,
        trip_id: int,
        version: int,
        **kwargs,
    ) -> Itinerary:
        """
        Create a new itinerary.

        Args:
            db: SQLAlchemy session
            trip_id: Parent trip ID
            version: Itinerary version (must be unique per trip)
            **kwargs: Additional itinerary attributes

        Returns:
            Created Itinerary instance
        """
        itinerary = Itinerary(
            trip_id=trip_id,
            version=version,
            **kwargs,
        )
        db.add(itinerary)
        db.commit()
        db.refresh(itinerary)
        return itinerary

    @staticmethod
    def get_by_id(db: Session, itinerary_id: int) -> Itinerary | None:
        """Get itinerary by ID."""
        return db.get(Itinerary, itinerary_id)

    @staticmethod
    def get_by_trip_and_version(
        db: Session,
        trip_id: int,
        version: int,
    ) -> Itinerary | None:
        """Get itinerary by trip ID and version."""
        stmt = select(Itinerary).where(
            and_(
                Itinerary.trip_id == trip_id,
                Itinerary.version == version,
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_by_trip(
        db: Session,
        trip_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Itinerary]:
        """List itineraries for a trip, ordered by version descending."""
        stmt = (
            select(Itinerary)
            .where(Itinerary.trip_id == trip_id)
            .offset(skip)
            .limit(limit)
            .order_by(Itinerary.version.desc())
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_latest_by_trip(db: Session, trip_id: int) -> Itinerary | None:
        """Get the latest (highest version) itinerary for a trip."""
        stmt = (
            select(Itinerary)
            .where(Itinerary.trip_id == trip_id)
            .order_by(Itinerary.version.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def update(db: Session, itinerary: Itinerary, **kwargs) -> Itinerary:
        """Update itinerary attributes."""
        for key, value in kwargs.items():
            setattr(itinerary, key, value)
        db.commit()
        db.refresh(itinerary)
        return itinerary

    @staticmethod
    def delete(db: Session, itinerary: Itinerary) -> None:
        """Delete an itinerary."""
        db.delete(itinerary)
        db.commit()

    # ItineraryStop operations

    @staticmethod
    def create_stop(
        db: Session,
        itinerary_id: int,
        destination_id: int,
        sequence: int,
        **kwargs,
    ) -> ItineraryStop:
        """Create a new itinerary stop."""
        stop = ItineraryStop(
            itinerary_id=itinerary_id,
            destination_id=destination_id,
            sequence=sequence,
            **kwargs,
        )
        db.add(stop)
        db.commit()
        db.refresh(stop)
        return stop

    @staticmethod
    def get_stop_by_id(db: Session, stop_id: int) -> ItineraryStop | None:
        """Get itinerary stop by ID."""
        return db.get(ItineraryStop, stop_id)

    @staticmethod
    def list_stops_by_itinerary(
        db: Session,
        itinerary_id: int,
    ) -> list[ItineraryStop]:
        """List all stops for an itinerary, ordered by sequence."""
        stmt = (
            select(ItineraryStop)
            .where(ItineraryStop.itinerary_id == itinerary_id)
            .order_by(ItineraryStop.sequence)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update_stop(db: Session, stop: ItineraryStop, **kwargs) -> ItineraryStop:
        """Update itinerary stop attributes."""
        for key, value in kwargs.items():
            setattr(stop, key, value)
        db.commit()
        db.refresh(stop)
        return stop

    @staticmethod
    def delete_stop(db: Session, stop: ItineraryStop) -> None:
        """Delete an itinerary stop."""
        db.delete(stop)
        db.commit()
