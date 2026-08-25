"""Trip domain model."""

from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.feedback import Feedback
    from app.models.itinerary import Itinerary
    from app.models.user import User


class TripStatus(str, Enum):
    """Status of a trip."""

    DRAFT = "draft"
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransportMode(str, Enum):
    """Primary transport mode for a trip."""

    WALKING = "walking"
    DRIVING = "driving"
    PUBLIC_TRANSPORT = "public_transport"
    BICYCLING = "bicycling"
    FLIGHT = "flight"
    MIXED = "mixed"


class BudgetLevel(str, Enum):
    """Budget level for a trip."""

    ECONOMY = "economy"
    MID_RANGE = "mid_range"
    LUXURY = "luxury"
    CUSTOM = "custom"


class Trip(Base, TimestampMixin):
    """
    Trip represents a user's travel planning requirements.

    Responsibilities:
    - Store user's trip planning parameters
    - Track trip status through its lifecycle
    - Provide foundation for itinerary generation
    - Maintain extensibility for future requirements

    Constraints:
    - User ID is required
    - Title is required
    - Start date/location are required
    - Status defaults to DRAFT
    """

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Trip identification
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location and timing
    start_location: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Duration information (in minutes)
    available_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Budget
    budget_level: Mapped[BudgetLevel] = mapped_column(
        String(20),
        nullable=False,
        default=BudgetLevel.MID_RANGE,
    )
    budget_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Transport
    transport_mode: Mapped[TransportMode] = mapped_column(
        String(20),
        nullable=False,
        default=TransportMode.MIXED,
    )

    # Preferences (extensible via JSON or separate tables in future)
    preferences: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Status
    status: Mapped[TripStatus] = mapped_column(
        String(20),
        nullable=False,
        default=TripStatus.DRAFT,
    )

    # Metadata
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="trips")
    itineraries: Mapped[list[Itinerary]] = relationship(
        "Itinerary",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="trip",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "available_duration_minutes IS NULL OR available_duration_minutes > 0",
            name="duration_positive",
        ),
        CheckConstraint(
            "budget_amount IS NULL OR budget_amount >= 0",
            name="budget_positive",
        ),
        CheckConstraint(
            "end_date IS NULL OR start_date <= end_date",
            name="dates_valid",
        ),
    )

    @property
    def is_ready_for_planning(self) -> bool:
        """Check if trip has minimum requirements for itinerary generation."""
        return bool(
            self.status in (TripStatus.PLANNING, TripStatus.DRAFT)
            and self.start_location
            and self.start_date
        )
