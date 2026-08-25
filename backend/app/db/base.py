"""Base SQLAlchemy model configuration with PostGIS support."""

from typing import ClassVar

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models with PostGIS support."""

    type_annotation_map: ClassVar[dict[type, type]] = {
        Geometry: Geometry,
    }

    def __repr__(self) -> str:
        """Generate string representation of the model instance."""
        cols = []
        for col_desc in self.__table__.columns:
            col = col_desc.name
            if col.startswith("_"):
                continue
            val = getattr(self, col, None)
            cols.append(f"{col}={val!r}")
        return f"{self.__class__.__name__}({', '.join(cols)})"


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
