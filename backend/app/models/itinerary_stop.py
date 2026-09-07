"""ItineraryStop domain model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.destination import Destination
    from app.models.itinerary import Itinerary


class ItineraryStop(Base, TimestampMixin):
    """
    ItineraryStop represents an ordered destination in an itinerary.

    Responsibilities:
    - Store sequence/order of stops
    - Track planned timing for each stop
    - Store travel estimates between stops
    - Link to destination with additional context

    Constraints:
    - Itinerary ID is required
    - Destination ID is required
    - Sequence is required and unique per itinerary
    """

    __tablename__ = "itinerary_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    itinerary_id: Mapped[int] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sequence in the itinerary (1-based)
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Timing
    planned_arrival: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    planned_departure: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Duration at this stop (in minutes)
    visit_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Travel estimates from previous stop
    estimated_travel_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    estimated_travel_distance_km: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Travel mode for this segment (can differ from trip default)
    travel_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Selection metadata
    selection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cost estimate for this stop
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Relationships
    itinerary: Mapped[Itinerary] = relationship(
        "Itinerary",
        back_populates="stops",
    )
    destination: Mapped[Destination] = relationship(
        "Destination",
        back_populates="itinerary_stops",
    )

    __table_args__ = (
        # Unique sequence per itinerary
    )
