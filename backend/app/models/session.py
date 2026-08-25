"""Session domain model for persistent login architecture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class SessionStatus(str):
    """Session status enumeration."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Session(Base, TimestampMixin):
    """
    Session represents a server-side session for persistent login.

    Responsibilities:
    - Track authenticated user sessions
    - Store session metadata without raw secrets
    - Support secure session invalidation

    Constraints:
    - Session token must be unique
    - User ID is required
    - Expiration is required
    - Status tracks session state

    Architecture Note:
    This model supports the planned persistent-login architecture but does NOT
    implement authentication logic. The actual auth flow will be added later.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="sessions")

    __table_args__ = (
        # Index for active session lookups
    )

    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return self.expires_at < datetime.now(UTC)
