"""Add image URL to destinations.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional image URL to destinations."""
    op.add_column(
        "destinations",
        sa.Column(
            "image_url",
            sa.String(length=1000),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove destination image URL."""
    op.drop_column(
        "destinations",
        "image_url",
    )