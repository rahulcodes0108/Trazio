"""Destination domain model with PostGIS geographic support."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.feedback import Feedback
    from app.models.itinerary_stop import ItineraryStop


class DestinationCategory(str, Enum):
    """Category of a destination."""

    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    NATURE = "nature"
    CULTURAL = "cultural"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class DestinationSourceStatus(str, Enum):
    """Verification status of a destination source."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    OUTDATED = "outdated"


class AccessibilityLevel(str, Enum):
    """Accessibility level of a destination."""

    FULLY_ACCESSIBLE = "fully_accessible"
    PARTIALLY_ACCESSIBLE = "partially_accessible"
    NOT_ACCESSIBLE = "not_accessible"
    UNKNOWN = "unknown"


class Destination(Base, TimestampMixin):
    """
    Destination represents a tourism location/point of interest.

    Responsibilities:
    - Store geographic and descriptive information about destinations
    - Support geospatial queries via PostGIS
    - Track popularity and accessibility
    - Provide foundation for itinerary planning

    Constraints:
    - Name is required
    - Slug must be unique
    - Location (geometry) is required
    - Category is required
    - Active status defaults to True

    PostGIS Usage:
    - Uses Geometry type for location (POINT with SRID 4326)
    - Spatial index created for efficient geographic queries
    """

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(
    String(1000),
    nullable=True,
    )
    category: Mapped[DestinationCategory] = mapped_column(
    SQLEnum(
        DestinationCategory,
        values_callable=lambda enum_class: [item.value for item in enum_class],
        name="destinationcategory",
        native_enum=True,),
    nullable=False,
    default=DestinationCategory.ATTRACTION,
    )
    # PostGIS Geometry: POINT(lon lat) in SRID 4326 (WGS84)
    location: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # Address information
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    state_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Operating information
    opening_hours: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entry_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_fee_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    average_visit_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Accessibility
    accessibility: Mapped[AccessibilityLevel] = mapped_column(
        SQLEnum(
            AccessibilityLevel,
            values_callable=lambda enum_class: [item.value for item in enum_class],
            native_enum=True,
            name="accessibilitylevel",
        ),
        nullable=False,
        default=AccessibilityLevel.UNKNOWN,
    )
    accessibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Popularity and status
    popularity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Metadata
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    sources: Mapped[list[DestinationSource]] = relationship(
        "DestinationSource",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    itinerary_stops: Mapped[list[ItineraryStop]] = relationship(
        "ItineraryStop",
        back_populates="destination",
        passive_deletes=True,
    )
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "popularity_score >= 0 AND popularity_score <= 100",
            name="popularity_score_check",
        ),
        CheckConstraint(
            "average_visit_duration_minutes IS NULL OR average_visit_duration_minutes > 0",
            name="visit_duration_check",
        ),
    )


class DestinationSource(Base, TimestampMixin):
    """
    DestinationSource tracks the provenance of destination information.

    Responsibilities:
    - Record where destination data originated
    - Track verification status
    - Support data attribution and trust scoring

    Constraints:
    - Destination ID is required
    - Source name is required
    - Reference must be unique per source
    """

    __tablename__ = "destination_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[DestinationSourceStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DestinationSourceStatus.PENDING,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    trust_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    destination: Mapped[Destination] = relationship(
        "Destination",
        back_populates="sources",
    )

    __table_args__ = (
        CheckConstraint(
            "trust_score >= 0 AND trust_score <= 100",
            name="trust_score_check",
        ),
    )
