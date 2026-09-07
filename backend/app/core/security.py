"""Security utilities for authentication: password hashing and JWT token management."""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with 12 rounds.

    Returns a UTF-8 decoded string of the hashed password.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(user_id: int) -> str:
    """Create a JWT access token for the given user ID.

    Token expires in ACCESS_TOKEN_EXPIRE_MINUTES (default: 15 minutes).
    """
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Decode and validate a JWT access token.

    Returns the user_id (as int) if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError):
        return None


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token.

    Uses secrets.token_hex(32) for 64-character hex string.
    """
    import secrets
    return secrets.token_hex(32)


def get_access_token_expiry() -> datetime:
    """Get the expiry datetime for a new access token."""
    return datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )


def get_refresh_token_expiry() -> datetime:
    """Get the expiry datetime for a new refresh token/session."""
    return datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
