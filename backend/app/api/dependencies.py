"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# OAuth2 scheme for Bearer token extraction
oauth2_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: DBSession = Depends(get_db),
) -> User:
    """Dependency that validates JWT access token and returns the user.

    Extracts the Bearer token from the Authorization header,
    decodes it to get the user_id, then retrieves and returns the User.

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 404: If user not found
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = AuthService.get_current_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
) -> int:
    """Dependency that validates JWT access token and returns the user ID.

    Lightweight version that only decodes the token without DB lookup.
    Use when user object is not needed, only the ID.

    Raises:
        HTTPException 401: If token is missing or invalid
    """
    token = credentials.credentials
    user_id = decode_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


def get_client_info(request: Request) -> dict[str, str | None]:
    """Extract client information from the request.

    Returns a dictionary with ip_address, user_agent, and device_info.
    """
    # Get IP address from headers (handling proxy headers)
    ip_address = request.client.host if request.client else None
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent")
    device_info = None  # Can be enhanced later

    return {
        "ip_address": ip_address,
        "user_agent": user_agent,
        "device_info": device_info,
    }
