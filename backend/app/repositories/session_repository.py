"""Repository for Session database operations.

The Session model is the server-side source of truth for authentication sessions.
The session_token column stores the refresh token.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.session import Session, SessionStatus


class SessionRepository:
    """Repository for Session database operations.

    Provides clean abstraction for Session CRUD operations supporting
    the persistent login architecture.
    """

    @staticmethod
    def create(
        db: DBSession,
        user_id: int,
        session_token: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> Session:
        """Create a new session for a user.

        Args:
            db: SQLAlchemy database session
            user_id: The user ID this session belongs to
            session_token: The refresh token (cryptographically secure)
            expires_at: When the session/refresh token expires
            ip_address: Client IP address
            user_agent: Client User-Agent string
            device_info: Client device information

        Returns:
            The created Session object
        """
        session = Session(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at,
            status=SessionStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_by_token(db: DBSession, token: str) -> Session | None:
        """Get a session by its token (refresh token).

        Only returns ACTIVE sessions that have not expired.
        """
        from sqlalchemy import and_
        from datetime import UTC, datetime

        stmt = select(Session).where(
            and_(
                Session.session_token == token,
                Session.status == SessionStatus.ACTIVE,
                Session.expires_at > datetime.now(UTC),
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: DBSession, session_id: int) -> Session | None:
        """Get a session by its ID."""
        return db.get(Session, session_id)

    @staticmethod
    def get_active_by_user(db: DBSession, user_id: int) -> list[Session]:
        """Get all active sessions for a user."""
        from sqlalchemy import and_
        from datetime import UTC, datetime

        stmt = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.status == SessionStatus.ACTIVE,
                Session.expires_at > datetime.now(UTC),
            )
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def revoke(db: DBSession, session: Session) -> Session:
        """Revoke a session by setting its status to REVOKED.

        Args:
            db: SQLAlchemy database session
            session: The Session object to revoke

        Returns:
            The revoked Session object
        """
        session.status = SessionStatus.REVOKED
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def revoke_by_token(db: DBSession, token: str) -> Session | None:
        """Revoke a session by its token.

        Returns the revoked session or None if not found.
        """
        session = db.get(Session, token)
        if session is None:
            return None
        return SessionRepository.revoke(db, session)

    @staticmethod
    def revoke_all_by_user(db: DBSession, user_id: int, except_session_id: int | None = None) -> int:
        """Revoke all sessions for a user except optionally one.

        Args:
            db: SQLAlchemy database session
            user_id: The user ID
            except_session_id: If provided, don't revoke this session

        Returns:
            Number of sessions revoked
        """
        from sqlalchemy import and_, or_
        from datetime import UTC, datetime

        # Find active sessions for this user
        stmt = select(Session).where(
            and_(
                Session.user_id == user_id,
                Session.status == SessionStatus.ACTIVE,
                Session.expires_at > datetime.now(UTC),
            )
        )
        if except_session_id is not None:
            stmt = stmt.where(Session.id != except_session_id)

        sessions = list(db.execute(stmt).scalars().all())

        count = 0
        for session in sessions:
            SessionRepository.revoke(db, session)
            count += 1

        return count

    @staticmethod
    def delete(db: DBSession, session: Session) -> None:
        """Delete a session from the database."""
        db.delete(session)
        db.commit()
