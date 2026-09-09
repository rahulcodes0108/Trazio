"""Pydantic schemas for API request/response models."""

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserStatus
from app.models.destination import DestinationCategory, AccessibilityLevel
from app.models.trip import TripStatus, TransportMode, BudgetLevel
from app.models.itinerary import ItineraryStatus


# =============================================================================
# Authentication Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    username: str = Field(..., min_length=1, max_length=50)


class UserRegister(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email_or_username: str = Field(..., description="User email or username")
    password: str = Field(..., description="User password")


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Schema for logout request."""
    refresh_token: str = Field(..., description="Refresh token to invalidate")


# =============================================================================
# Token Schemas
# =============================================================================

class Token(BaseModel):
    """Access token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class TokenWithRefresh(Token):
    """Token response with refresh token (login response)."""
    refresh_token: str


# =============================================================================
# User Schemas
# =============================================================================

class UserPublic(BaseModel):
    """Public user profile schema."""
    id: int
    email: EmailStr
    username: str
    full_name: str | None
    is_verified: bool
    status: UserStatus
    created_at: datetime


class UserMe(UserPublic):
    """Current user profile with additional info."""
    pass


# =============================================================================
# Session Schemas
# =============================================================================

class SessionPublic(BaseModel):
    """Public session schema (limited info)."""
    id: int
    user_id: int
    expires_at: datetime
    status: str
    ip_address: str | None
    device_info: str | None


# =============================================================================
# Message Schemas
# =============================================================================

class Message(BaseModel):
    """Simple message response schema."""
    detail: str


class ErrorDetail(BaseModel):
    """Error detail schema."""
    detail: str


# =============================================================================
# Destination Schemas
# =============================================================================

class DestinationBase(BaseModel):
    """Base destination schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=10000)
    image_url: str | None = Field(None, max_length=1000)
    category: DestinationCategory = Field(..., description="Category of the destination")
    location: str = Field(..., description="Location as WKT string (POINT(lon lat))")
    address_line1: str | None = Field(None, max_length=200)
    address_line2: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=100)
    state_province: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str | None = Field(None, max_length=100)
    opening_hours: str | None = Field(None, max_length=500)
    entry_fee: float | None = Field(None, ge=0)
    entry_fee_currency: str | None = Field(None, max_length=3)
    average_visit_duration_minutes: int | None = Field(None, ge=1)
    accessibility: AccessibilityLevel = Field(
        default=AccessibilityLevel.UNKNOWN, description="Accessibility level"
    )
    accessibility_notes: str | None = Field(None, max_length=10000)
    popularity_score: float = Field(default=0.0, ge=0, le=100)
    is_active: bool = Field(default=True)
    website_url: str | None = Field(None, max_length=500)
    phone_number: str | None = Field(None, max_length=30)
    email: str | None = Field(None, max_length=255)


class DestinationPublic(DestinationBase):
    """Public destination schema with ID and timestamps."""
    id: int
    created_at: datetime
    updated_at: datetime


class DestinationListResponse(BaseModel):
    """Response schema for listing destinations."""
    destinations: list[DestinationPublic]
    count: int


# =============================================================================
# Destination Source Schemas
# =============================================================================

class DestinationSourceBase(BaseModel):
    """Base destination source schema."""
    source_name: str = Field(..., min_length=1, max_length=100)
    source_type: str | None = Field(None, max_length=50)
    source_reference: str = Field(..., min_length=1, max_length=255)
    source_url: str | None = Field(None, max_length=500)
    trust_score: float = Field(default=0.0, ge=0, le=100)
    notes: str | None = Field(None, max_length=10000)


class DestinationSourcePublic(DestinationSourceBase):
    """Public destination source schema with ID and timestamps."""
    id: int
    destination_id: int
    verification_status: str
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Trip Schemas
# =============================================================================

class TripBase(BaseModel):
    """Base trip schema with common fields."""
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=10000)
    start_location: str = Field(..., min_length=1, max_length=200)
    start_date: date = Field(..., description="Start date of the trip")
    start_time: time | None = Field(None, description="Start time of the trip")
    end_date: date | None = Field(None, description="End date of the trip")
    end_time: time | None = Field(None, description="End time of the trip")
    available_duration_minutes: int | None = Field(None, ge=1)
    budget_level: BudgetLevel = Field(default=BudgetLevel.MID_RANGE)
    budget_amount: float | None = Field(None, ge=0)
    budget_currency: str | None = Field(None, max_length=3)
    transport_mode: TransportMode = Field(default=TransportMode.MIXED)
    preferences: dict[str, Any] | None = Field(None, description="Trip preferences as JSON")
    status: TripStatus = Field(default=TripStatus.DRAFT)
    is_public: bool = Field(default=False)
    share_token: str | None = Field(None, max_length=64)


class TripCreate(TripBase):
    """Schema for creating a new trip."""
    pass


class TripUpdate(BaseModel):
    """Schema for updating a trip."""
    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=10000)
    start_location: str | None = Field(None, min_length=1, max_length=200)
    start_date: date | None = Field(None)
    start_time: time | None = Field(None)
    end_date: date | None = Field(None)
    end_time: time | None = Field(None)
    available_duration_minutes: int | None = Field(None, ge=1)
    budget_level: BudgetLevel | None = Field(None)
    budget_amount: float | None = Field(None, ge=0)
    budget_currency: str | None = Field(None, max_length=3)
    transport_mode: TransportMode | None = Field(None)
    preferences: dict[str, Any] | None = Field(None)
    status: TripStatus | None = Field(None)
    is_public: bool | None = Field(None)
    share_token: str | None = Field(None, max_length=64)


class TripPublic(TripBase):
    """Public trip schema with ID and timestamps."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class TripListResponse(BaseModel):
    """Response schema for listing trips."""
    trips: list[TripPublic]
    count: int


# =============================================================================
# Itinerary Schemas
# =============================================================================

class ItineraryBase(BaseModel):
    """Base itinerary schema with common fields."""
    version: int = Field(..., ge=1, description="Itinerary version number")
    status: ItineraryStatus = Field(default=ItineraryStatus.DRAFT)
    notes: str | None = Field(None, max_length=500)
    total_duration_minutes: int = Field(default=0, ge=0)
    estimated_travel_duration_minutes: int = Field(default=0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0)
    estimated_cost_currency: str | None = Field(None, max_length=3)
    is_optimized: bool = Field(default=False)


class ItineraryCreate(ItineraryBase):
    """Schema for creating a new itinerary."""
    pass


class ItineraryPublic(ItineraryBase):
    """Public itinerary schema with ID and timestamps."""
    id: int
    trip_id: int
    stop_count: int = Field(default=0, description="Number of stops in this itinerary")
    created_at: datetime
    updated_at: datetime


class ItineraryListResponse(BaseModel):
    """Response schema for listing itineraries."""
    itineraries: list[ItineraryPublic]
    count: int


# =============================================================================
# Itinerary Stop Schemas
# =============================================================================

class ItineraryStopBase(BaseModel):
    """Base itinerary stop schema."""
    destination_id: int = Field(..., ge=1)
    sequence: int = Field(..., ge=1, description="Sequence number in the itinerary")
    planned_arrival: datetime | None = Field(None, description="Planned arrival time")
    planned_departure: datetime | None = Field(None, description="Planned departure time")
    visit_duration_minutes: int | None = Field(None, ge=1)
    estimated_travel_duration_minutes: int | None = Field(None, ge=0)
    estimated_travel_distance_km: float | None = Field(None, ge=0)
    travel_mode: str | None = Field(None, max_length=50)
    selection_reason: str | None = Field(None, max_length=500)
    notes: str | None = Field(None, max_length=10000)
    estimated_cost: float | None = Field(None, ge=0)
    estimated_cost_currency: str | None = Field(None, max_length=3)


class ItineraryStopCreate(ItineraryStopBase):
    """Schema for creating a new itinerary stop."""
    pass


class ItineraryStopPublic(ItineraryStopBase):
    """Public itinerary stop schema with ID and timestamps."""
    id: int
    itinerary_id: int
    created_at: datetime
    updated_at: datetime


class ItineraryStopListResponse(BaseModel):
    """Response schema for listing itinerary stops."""
    stops: list[ItineraryStopPublic]
    count: int

class ReplanningRequest(BaseModel):
    """API request schema for dynamic itinerary replanning."""

    unavailable_destination_ids: list[int] = Field(
        ...,
        min_length=1,
        description="Destination IDs that became unavailable.",
    )

    reason: str | None = Field(
        None,
        max_length=500,
        description="Optional reason for the replanning request.",
    )

    @field_validator("unavailable_destination_ids")
    @classmethod
    def validate_destination_ids(cls, value: list[int]) -> list[int]:
        """Ensure all unavailable destination IDs are positive."""
        if any(destination_id < 1 for destination_id in value):
            raise ValueError(
                "Destination IDs must be greater than or equal to 1."
            )
        return value