"""Itinerary domain model with versioning support."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.itinerary_stop import ItineraryStop
    from app.models.trip import Trip


class ItineraryStatus(str, Enum):
    """Status of an itinerary."""

    DRAFT = "draft"
    GENERATED = "generated"
    OPTIMIZED = "optimized"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Itinerary(Base, TimestampMixin):
    """
    Itinerary represents a versioned travel plan for a trip.

    Responsibilities:
    - Store ordered stops for a trip
    - Support versioning for dynamic replanning
    - Track duration and cost estimates
    - Maintain relationship with trip

    Constraints:
    - Trip ID is required
    - Version is required and unique per trip
    - Status defaults to DRAFT

    Versioning Strategy:
    - Each trip can have multiple itinerary versions
    - Version number is monotonically increasing
    - Lower version numbers are kept for history/audit
    - Latest version is typically the active one
    """

    __tablename__ = "itineraries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Status and metadata
    status: Mapped[ItineraryStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ItineraryStatus.DRAFT,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Duration and cost estimates (in minutes and currency units)
    total_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    estimated_travel_duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    estimated_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    estimated_cost_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Optimized flag for future optimization features
    is_optimized: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="itineraries")
    stops: Mapped[list[ItineraryStop]] = relationship(
        "ItineraryStop",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ItineraryStop.sequence",
    )

    __table_args__ = (
        UniqueConstraint(
            "trip_id",
            "version",
            name="uq_itinerary_trip_version",
        ),
    )

    @property
    def stop_count(self) -> int:
        """Return the number of stops in this itinerary."""
        return len(self.stops) if self.stops else 0
