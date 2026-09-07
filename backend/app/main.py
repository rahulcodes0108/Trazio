"""Trazio FastAPI backend application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Trazio backend...")
    yield
    # Shutdown
    logger.info("Shutting down Trazio backend...")


app = FastAPI(
    title="Trazio API",
    description="Trazio tourism platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# Include API routers
from app.api.routers import auth_router, destinations_router, trips_router, itineraries_router

# Include routers
app.include_router(auth_router)
app.include_router(destinations_router)
app.include_router(trips_router)
app.include_router(itineraries_router)


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={"status": "healthy", "version": "0.1.0"},
        status_code=200,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
