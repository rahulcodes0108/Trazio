"""Service layer for Destination operations."""

from sqlalchemy.orm import Session

from app.models.destination import Destination, DestinationSource
from app.repositories.destination_repository import DestinationRepository


class DestinationService:
    """
    Service layer for Destination operations.

    Establishes clean boundary between API/application logic and
    the DestinationRepository.
    """

    @staticmethod
    def create_destination(
        db: Session,
        name: str,
        slug: str,
        location_wkt: str,
        **kwargs,
    ) -> Destination:
        """Create a new destination."""
        return DestinationRepository.create(
            db=db,
            name=name,
            slug=slug,
            location_wkt=location_wkt,
            **kwargs,
        )

    @staticmethod
    def get_destination_by_id(db: Session, destination_id: int) -> Destination | None:
        """Get destination by ID."""
        return DestinationRepository.get_by_id(db=db, destination_id=destination_id)

    @staticmethod
    def get_destination_by_slug(db: Session, slug: str) -> Destination | None:
        """Get destination by slug."""
        return DestinationRepository.get_by_slug(db=db, slug=slug)

    @staticmethod
    def list_destinations(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Destination]:
        """List all active destinations."""
        return DestinationRepository.list_active(db=db, skip=skip, limit=limit)

    @staticmethod
    def create_destination_source(
        db: Session,
        destination_id: int,
        source_name: str,
        source_reference: str,
        **kwargs,
    ) -> DestinationSource:
        """Create a destination source."""
        return DestinationRepository.create_source(
            db=db,
            destination_id=destination_id,
            source_name=source_name,
            source_reference=source_reference,
            **kwargs,
        )

    @staticmethod
    def get_destination_sources(
        db: Session,
        destination_id: int,
    ) -> list[DestinationSource]:
        """Get all sources for a destination."""
        return DestinationRepository.get_sources_by_destination(
            db=db,
            destination_id=destination_id,
        )
