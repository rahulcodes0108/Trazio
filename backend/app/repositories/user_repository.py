"""Repository for User database operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserStatus


class UserRepository:
    """
    Repository for User database operations.

    Provides clean abstraction for User CRUD operations.
    """

    @staticmethod
    def create(db: Session, email: str, username: str, hashed_password: str, **kwargs) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            **kwargs,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        """Get user by ID."""
        return db.get(User, user_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        """Get user by email."""
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_active(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """List active users with pagination."""
        stmt = select(User).where(User.status == UserStatus.ACTIVE).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update(db: Session, user: User, **kwargs) -> User:
        """Update user attributes."""
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete(db: Session, user: User) -> None:
        """Delete a user."""
        db.delete(user)
        db.commit()
