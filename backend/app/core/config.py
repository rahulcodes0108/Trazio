"""Application configuration using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@postgres:5432/trazio",
        description="PostgreSQL connection URL with PostGIS",
    )

        # Mapbox
    MAPBOX_ACCESS_TOKEN: str | None = Field(
        default=None,
        description="Mapbox public access token for geocoding and routing",
    )

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str | None = Field(
        default=None,
        description="Cloudinary cloud name for destination image uploads",
    )
    CLOUDINARY_API_KEY: str | None = Field(
        default=None,
        description="Cloudinary API key for destination image uploads",
    )
    CLOUDINARY_API_SECRET: str | None = Field(
        default=None,
        description="Cloudinary API secret for destination image uploads",
    )


    # Authentication
    JWT_SECRET_KEY: str = Field(
    description="JWT signing secret key",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


settings = Settings()
