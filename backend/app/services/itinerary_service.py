"""Service layer for Itinerary operations."""

from sqlalchemy.orm import Session

from app.models.itinerary import Itinerary
from app.models.itinerary_stop import ItineraryStop
from app.repositories.itinerary_repository import ItineraryRepository


class ItineraryService:
    """
    Service layer for Itinerary operations.

    Establishes clean boundary between API/application logic and
    the ItineraryRepository.
    """

    @staticmethod
    def create_itinerary(
        db: Session,
        trip_id: int,
        version: int,
        **kwargs,
    ) -> Itinerary:
        """Create a new itinerary."""
        return ItineraryRepository.create(
            db=db,
            trip_id=trip_id,
            version=version,
            **kwargs,
        )

    @staticmethod
    def get_itinerary_by_id(db: Session, itinerary_id: int) -> Itinerary | None:
        """Get itinerary by ID."""
        return ItineraryRepository.get_by_id(db=db, itinerary_id=itinerary_id)

    @staticmethod
    def get_itinerary_by_trip_and_version(
        db: Session,
        trip_id: int,
        version: int,
    ) -> Itinerary | None:
        """Get itinerary by trip ID and version."""
        return ItineraryRepository.get_by_trip_and_version(
            db=db,
            trip_id=trip_id,
            version=version,
        )

    @staticmethod
    def list_itineraries_by_trip(
        db: Session,
        trip_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Itinerary]:
        """List itineraries for a trip."""
        return ItineraryRepository.list_by_trip(
            db=db,
            trip_id=trip_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_latest_itinerary_by_trip(db: Session, trip_id: int) -> Itinerary | None:
        """Get the latest itinerary for a trip."""
        return ItineraryRepository.get_latest_by_trip(db=db, trip_id=trip_id)

    @staticmethod
    def create_itinerary_stop(
        db: Session,
        itinerary_id: int,
        destination_id: int,
        sequence: int,
        **kwargs,
    ) -> ItineraryStop:
        """Create a new itinerary stop."""
        return ItineraryRepository.create_stop(
            db=db,
            itinerary_id=itinerary_id,
            destination_id=destination_id,
            sequence=sequence,
            **kwargs,
        )

    @staticmethod
    def list_itinerary_stops(
        db: Session,
        itinerary_id: int,
    ) -> list[ItineraryStop]:
        """List all stops for an itinerary."""
        return ItineraryRepository.list_stops_by_itinerary(
            db=db,
            itinerary_id=itinerary_id,
        )
