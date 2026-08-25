"""Service layer for User operations."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    """
    Service layer for User operations.

    Establishes clean boundary between API/application logic and
    the UserRepository.
    """

    @staticmethod
    def create_user(
        db: Session,
        email: str,
        username: str,
        hashed_password: str,
        **kwargs,
    ) -> User:
        """Create a new user."""
        return UserRepository.create(
            db=db,
            email=email,
            username=username,
            hashed_password=hashed_password,
            **kwargs,
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User | None:
        """Get user by ID."""
        return UserRepository.get_by_id(db=db, user_id=user_id)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """Get user by email."""
        return UserRepository.get_by_email(db=db, email=email)

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        """Get user by username."""
        return UserRepository.get_by_username(db=db, username=username)

    @staticmethod
    def list_active_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """List active users."""
        return UserRepository.list_active(db=db, skip=skip, limit=limit)
