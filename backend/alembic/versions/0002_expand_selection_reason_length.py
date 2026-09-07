"""Expand itinerary stop selection reason length.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    """Expand itinerary stop selection reason to support personalization explanations."""
    op.alter_column(
        "itinerary_stops",
        "selection_reason",
        existing_type=sa.String(length=200),
        type_=sa.String(length=500),
        existing_nullable=True,
    )


def downgrade():
    """Restore the original selection reason length."""
    op.alter_column(
        "itinerary_stops",
        "selection_reason",
        existing_type=sa.String(length=500),
        type_=sa.String(length=200),
        existing_nullable=True,
    )
