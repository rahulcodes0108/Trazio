"""Repository for Destination database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.destination import Destination, DestinationCategory, DestinationSource


class DestinationRepository:
    """
    Repository for Destination database operations.

    Provides clean abstraction for Destination CRUD operations
    and basic geospatial queries.
    """

    @staticmethod
    def create(db: Session, name: str, slug: str, location_wkt: str, **kwargs) -> Destination:
        """
        Create a new destination.

        Args:
            db: SQLAlchemy session
            name: Destination name
            slug: Unique slug
            location_wkt: Location as WKT string (e.g., 'POINT(lon lat)')
            **kwargs: Additional destination attributes

        Returns:
            Created Destination instance
        """
        destination = Destination(
            name=name,
            slug=slug,
            location=location_wkt,
            **kwargs,
        )
        db.add(destination)
        db.commit()
        db.refresh(destination)
        return destination

    @staticmethod
    def get_by_id(db: Session, destination_id: int) -> Destination | None:
        """Get destination by ID."""
        return db.get(Destination, destination_id)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Destination | None:
        """Get destination by slug."""
        stmt = select(Destination).where(Destination.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_by_category(
        db: Session,
        category: DestinationCategory,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Destination]:
        """List destinations by category with pagination."""
        stmt = (
            select(Destination)
            .where(Destination.category == category)
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_active(db: Session, skip: int = 0, limit: int = 100) -> list[Destination]:
        """List active destinations with pagination."""
        stmt = (
            select(Destination)
            .where(Destination.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def search_by_name(
        db: Session,
        name_pattern: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Destination]:
        """Search destinations by name pattern."""
        stmt = (
            select(Destination)
            .where(Destination.name.ilike(f"%{name_pattern}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update(db: Session, destination: Destination, **kwargs) -> Destination:
        """Update destination attributes."""
        for key, value in kwargs.items():
            setattr(destination, key, value)
        db.commit()
        db.refresh(destination)
        return destination

    @staticmethod
    def delete(db: Session, destination: Destination) -> None:
        """Delete a destination."""
        db.delete(destination)
        db.commit()

    # DestinationSource operations

    @staticmethod
    def create_source(
        db: Session,
        destination_id: int,
        source_name: str,
        source_reference: str,
        **kwargs,
    ) -> DestinationSource:
        """Create a new destination source."""
        source = DestinationSource(
            destination_id=destination_id,
            source_name=source_name,
            source_reference=source_reference,
            **kwargs,
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source

    @staticmethod
    def get_sources_by_destination(
        db: Session,
        destination_id: int,
    ) -> list[DestinationSource]:
        """Get all sources for a destination."""
        stmt = select(DestinationSource).where(
            DestinationSource.destination_id == destination_id
        )
        return list(db.execute(stmt).scalars().all())
