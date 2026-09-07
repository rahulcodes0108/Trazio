"""Auth API router for authentication endpoints.

Provides endpoints for user registration, login, logout, token refresh,
and current user retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_client_info, get_current_user
from app.api.schemas import (
    LogoutRequest,
    Message,
    RefreshTokenRequest,
    Token,
    TokenWithRefresh,
    UserLogin,
    UserMe,
    UserRegister,
)
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

# Security scheme for Bearer token (used by dependencies)
security = HTTPBearer()


@router.post(
    "/register",
    response_model=TokenWithRefresh,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account and return access + refresh tokens.",
)
async def register(
    request: Request,
    user_data: UserRegister,
    db: DBSession = Depends(get_db),
) -> TokenWithRefresh:
    """Register a new user.

    Creates a new user with the provided credentials and immediately
    logs them in by creating a session and returning tokens.
    """
    client_info = get_client_info(request)

    try:
        user = AuthService.register(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Auto-login the user
    token_data = AuthService.login(
        db=db,
        email_or_username=user.email,
        password=user_data.password,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"],
    )

    return TokenWithRefresh(**token_data)


@router.post(
    "/login",
    response_model=TokenWithRefresh,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user and return access + refresh tokens.",
)
async def login(
    request: Request,
    credentials: UserLogin,
    db: DBSession = Depends(get_db),
) -> TokenWithRefresh:
    """Login a user with email/username and password.

    Creates a new session (revoking any existing ones) and returns
    access token + refresh token.
    """
    client_info = get_client_info(request)

    try:
        token_data = AuthService.login(
            db=db,
            email_or_username=credentials.email_or_username,
            password=credentials.password,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            device_info=client_info["device_info"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenWithRefresh(**token_data)


@router.post(
    "/logout",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Invalidate the session associated with the refresh token.",
)
async def logout(
    logout_request: LogoutRequest,
    db: DBSession = Depends(get_db),
) -> Message:
    """Logout by revoking the session.

    The refresh token is used to find and revoke the session.
    """
    success = AuthService.logout(db, logout_request.refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    return Message(detail="Successfully logged out")


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token.",
)
async def refresh(
    refresh_request: RefreshTokenRequest,
    db: DBSession = Depends(get_db),
) -> Token:
    """Refresh the access token using a refresh token.

    Validates the refresh token against the server-side session store
    and returns a new access token.
    """
    try:
        token_data = AuthService.refresh(db, refresh_request.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(**token_data)


# =============================================================================
# Current User Endpoint (requires access token)
# =============================================================================

@router.get(
    "/me",
    response_model=UserMe,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Return the authenticated user's profile information.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserMe:
    """Get the current authenticated user's profile.

    Requires a valid Bearer access token in the Authorization header.
    """
    return UserMe(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_verified=current_user.is_verified,
        status=current_user.status,
        created_at=current_user.created_at,
    )
