"""User domain model."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.feedback import Feedback
    from app.models.session import Session
    from app.models.trip import Trip


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base, TimestampMixin):
    """
    User represents a registered user of the Trazio platform.

    Responsibilities:
    - Authenticate and authorize actions
    - Own trips and associated data
    - Store profile information

    Constraints:
    - Email must be unique
    - Username must be unique
    - Email is required and validated
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        String(20),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    sessions: Mapped[list[Session]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    trips: Mapped[list[Trip]] = relationship(
        "Trip",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    feedbacks: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Index for frequently queried fields
    )
