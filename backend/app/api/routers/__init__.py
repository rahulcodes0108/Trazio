"""API routers package."""

from app.api.routers.auth import router as auth_router
from app.api.routers.destinations import router as destinations_router
from app.api.routers.trips import router as trips_router
from app.api.routers.itineraries import router as itineraries_router

__all__ = ["auth_router", "destinations_router", "trips_router", "itineraries_router"]
