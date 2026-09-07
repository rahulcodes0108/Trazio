"""Service layer for authentication operations.

Handles user registration, login, logout, session management, and token operations.
Uses PostgreSQL Session model as the server-side source of truth.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_access_token_expiry,
    get_refresh_token_expiry,
    hash_password,
    verify_password,
)
from app.models.session import Session, SessionStatus
from app.models.user import User, UserStatus
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service layer for authentication operations.

    Establishes clean boundary between API/application logic and
    the repository layer for authentication.
    """

    @staticmethod
    def register(
        db: DBSession,
        email: str,
        username: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        """Register a new user.

        Args:
            db: SQLAlchemy database session
            email: User email (must be unique)
            username: User username (must be unique)
            password: Plain text password (will be hashed)
            full_name: Optional full name

        Returns:
            The created User object

        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists
        existing = UserRepository.get_by_email(db, email)
        if existing is not None:
            raise ValueError("User with this email already exists")

        existing = UserRepository.get_by_username(db, username)
        if existing is not None:
            raise ValueError("User with this username already exists")

        hashed_password = hash_password(password)
        return UserRepository.create(
            db=db,
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            status=UserStatus.ACTIVE,
            is_verified=False,
        )

    @staticmethod
    def login(
        db: DBSession,
        email_or_username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_info: str | None = None,
    ) -> dict[str, Any]:
        """Authenticate a user and create a new session.

        Args:
            db: SQLAlchemy database session
            email_or_username: User email or username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client User-Agent string
            device_info: Client device information

        Returns:
            Dictionary with access_token, refresh_token, token_type, expires_at

        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email or username
        user = UserRepository.get_by_email(db, email_or_username)
        if user is None:
            user = UserRepository.get_by_username(db, email_or_username)

        if user is None or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        if user.status != UserStatus.ACTIVE:
            raise ValueError("User account is not active")

        # Revoke any existing sessions for this user
        SessionRepository.revoke_all_by_user(db, user.id)

        # Create new session with refresh token
        refresh_token = generate_refresh_token()
        expires_at = get_refresh_token_expiry()

        SessionRepository.create(
            db=db,
            user_id=user.id,
            session_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=device_info,
        )

        # Generate access token
        access_token = create_access_token(user.id)
        access_expires_at = get_access_token_expiry()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_at": access_expires_at.isoformat(),
        }

    @staticmethod
    def logout(db: DBSession, session_token: str) -> bool:
        """Log out by revoking the session.

        Args:
            db: SQLAlchemy database session
            session_token: The refresh token to revoke

        Returns:
            True if session was revoked, False if not found
        """
        session = SessionRepository.get_by_token(db, session_token)
        if session is None:
            return False
        SessionRepository.revoke(db, session)
        return True

    @staticmethod
    def logout_all(db: DBSession, user_id: int) -> int:
        """Log out all sessions for a user.

        Args:
            db: SQLAlchemy database session
            user_id: The user ID

        Returns:
            Number of sessions revoked
        """
        return SessionRepository.revoke_all_by_user(db, user_id)

    @staticmethod
    def refresh(db: DBSession, refresh_token: str) -> dict[str, Any]:
        """Refresh an access token using a valid refresh token.

        Args:
            db: SQLAlchemy database session
            refresh_token: The refresh token from the client

        Returns:
            Dictionary with new access_token, token_type, expires_at

        Raises:
            ValueError: If refresh token is invalid or expired
        """
        session = SessionRepository.get_by_token(db, refresh_token)
        if session is None:
            raise ValueError("Invalid or expired refresh token")

        # Generate new access token
        access_token = create_access_token(session.user_id)
        access_expires_at = get_access_token_expiry()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_at": access_expires_at.isoformat(),
        }

    @staticmethod
    def validate_session(db: DBSession, refresh_token: str) -> bool:
        """Validate that a refresh token/session is still valid.

        Args:
            db: SQLAlchemy database session
            refresh_token: The refresh token to validate

        Returns:
            True if valid, False otherwise
        """
        return SessionRepository.get_by_token(db, refresh_token) is not None

    @staticmethod
    def get_current_user(db: DBSession, user_id: int) -> User | None:
        """Get a user by ID if they exist and are active.

        Args:
            db: SQLAlchemy database session
            user_id: The user ID

        Returns:
            User object or None
        """
        user = UserRepository.get_by_id(db, user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            return None
        return user

    @staticmethod
    def get_session_by_token(db: DBSession, refresh_token: str) -> Session | None:
        """Get a session by its refresh token.

        Args:
            db: SQLAlchemy database session
            refresh_token: The refresh token

        Returns:
            Session object or None
        """
        return SessionRepository.get_by_token(db, refresh_token)

    @staticmethod
    def get_active_sessions(db: DBSession, user_id: int) -> list[Session]:
        """Get all active sessions for a user.

        Args:
            db: SQLAlchemy database session
            user_id: The user ID

        Returns:
            List of active Session objects
        """
        return SessionRepository.get_active_by_user(db, user_id)
