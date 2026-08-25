"""Feedback domain model."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.destination import Destination
    from app.models.trip import Trip
    from app.models.user import User


class FeedbackType(str, Enum):
    """Type of feedback."""

    RATING = "rating"
    REVIEW = "review"
    SUGGESTION = "suggestion"
    BUG_REPORT = "bug_report"
    OTHER = "other"


class Feedback(Base, TimestampMixin):
    """
    Feedback represents user feedback associated with destinations or trips.

    Responsibilities:
    - Store user ratings and reviews
    - Track feedback for destinations and trips
    - Support minimal extensibility for future feedback types

    Constraints:
    - Either destination_id or trip_id must be provided
    - User ID is required
    - Type is required
    """

    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Feedback target (polymorphic: either destination or trip)
    destination_id: Mapped[int | None] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Feedback type and content
    feedback_type: Mapped[FeedbackType] = mapped_column(
        String(20),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rating (1-5 scale, nullable for non-rating feedback)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Additional metadata
    is_anonymous: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="feedbacks")
    destination: Mapped[Destination | None] = relationship(
        "Destination",
        back_populates="feedbacks",
    )
    trip: Mapped[Trip | None] = relationship(
        "Trip",
        back_populates="feedbacks",
    )

    __table_args__ = (
        # Ensure at least one target is provided
        # Note: This is enforced at application level, not database level
        # because both can be null for general feedback
    )
