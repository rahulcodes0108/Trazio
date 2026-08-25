"""Initial schema with PostGIS support.

Revision ID: 0001
Revises:
Create Date: 2026-08-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial schema with PostGIS extension and all domain tables."""
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")

    # Create enum types
    # UserStatus
    op.execute("""
        CREATE TYPE userstatus AS ENUM (
            'active',
            'inactive',
            'suspended'
        )
    """)

    # SessionStatus
    op.execute("""
        CREATE TYPE sessionstatus AS ENUM (
            'active',
            'expired',
            'revoked'
        )
    """)

    # DestinationCategory
    op.execute("""
        CREATE TYPE destinationcategory AS ENUM (
            'attraction',
            'restaurant',
            'accommodation',
            'transport',
            'shopping',
            'nature',
            'cultural',
            'entertainment',
            'other'
        )
    """)

    # DestinationSourceStatus
    op.execute("""
        CREATE TYPE destinationsourcestatus AS ENUM (
            'pending',
            'verified',
            'rejected',
            'outdated'
        )
    """)

    # AccessibilityLevel
    op.execute("""
        CREATE TYPE accessibilitylevel AS ENUM (
            'fully_accessible',
            'partially_accessible',
            'not_accessible',
            'unknown'
        )
    """)

    # TripStatus
    op.execute("""
        CREATE TYPE tripstatus AS ENUM (
            'draft',
            'planning',
            'confirmed',
            'in_progress',
            'completed',
            'cancelled'
        )
    """)

    # TransportMode
    op.execute("""
        CREATE TYPE transportmode AS ENUM (
            'walking',
            'driving',
            'public_transport',
            'bicycling',
            'flight',
            'mixed'
        )
    """)

    # BudgetLevel
    op.execute("""
        CREATE TYPE budgetlevel AS ENUM (
            'economy',
            'mid_range',
            'luxury',
            'custom'
        )
    """)

    # ItineraryStatus
    op.execute("""
        CREATE TYPE itinerarystatus AS ENUM (
            'draft',
            'generated',
            'optimized',
            'confirmed',
            'in_progress',
            'completed',
            'archived'
        )
    """)

    # FeedbackType
    op.execute("""
        CREATE TYPE feedbacktype AS ENUM (
            'rating',
            'review',
            'suggestion',
            'bug_report',
            'other'
        )
    """)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False, index=True),
        sa.Column("username", sa.String(length=50), nullable=False, index=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", "suspended", name="userstatus"), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("session_token", sa.String(length=255), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("status", sa.Enum("active", "expired", "revoked", name="sessionstatus"), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("device_info", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_token"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create destinations table with PostGIS geometry
    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False, index=True),
        sa.Column("slug", sa.String(length=120), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Enum("attraction", "restaurant", "accommodation", "transport", "shopping", "nature", "cultural", "entertainment", "other", name="destinationcategory"), nullable=False),
        sa.Column("location", postgresql.GEOMETRY(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("address_line1", sa.String(length=200), nullable=True),
        sa.Column("address_line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True, index=True),
        sa.Column("state_province", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True, index=True),
        sa.Column("opening_hours", sa.String(length=500), nullable=True),
        sa.Column("entry_fee", sa.Float(), nullable=True),
        sa.Column("entry_fee_currency", sa.String(length=3), nullable=True),
        sa.Column("average_visit_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("accessibility", sa.Enum("fully_accessible", "partially_accessible", "not_accessible", "unknown", name="accessibilitylevel"), nullable=False),
        sa.Column("accessibility_notes", sa.Text(), nullable=True),
        sa.Column("popularity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint("popularity_score >= 0 AND popularity_score <= 100", name="popularity_score_check"),
        sa.CheckConstraint("average_visit_duration_minutes IS NULL OR average_visit_duration_minutes > 0", name="visit_duration_check"),
    )

    # Create spatial index for destinations
    op.execute("CREATE INDEX idx_destinations_location ON destinations USING GIST(location)")

    # Create destination_sources table
    op.create_table(
        "destination_sources",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("destination_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("verification_status", sa.Enum("pending", "verified", "rejected", "outdated", name="destinationsourcestatus"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="trust_score_check"),
    )

    # Create trips table
    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_location", sa.String(length=200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False, index=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True, index=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("available_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("budget_level", sa.Enum("economy", "mid_range", "luxury", "custom", name="budgetlevel"), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=True),
        sa.Column("budget_currency", sa.String(length=3), nullable=True),
        sa.Column("transport_mode", sa.Enum("walking", "driving", "public_transport", "bicycling", "flight", "mixed", name="transportmode"), nullable=False),
        sa.Column("preferences", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.Enum("draft", "planning", "confirmed", "in_progress", "completed", "cancelled", name="tripstatus"), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("share_token", sa.String(length=64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("available_duration_minutes IS NULL OR available_duration_minutes > 0", name="duration_positive"),
        sa.CheckConstraint("budget_amount IS NULL OR budget_amount >= 0", name="budget_positive"),
        sa.CheckConstraint("end_date IS NULL OR start_date <= end_date", name="dates_valid"),
    )

    # Create itineraries table
    op.create_table(
        "itineraries",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("trip_id", sa.Integer(), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("draft", "generated", "optimized", "confirmed", "in_progress", "completed", "archived", name="itinerarystatus"), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_travel_duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_cost_currency", sa.String(length=3), nullable=True),
        sa.Column("is_optimized", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "version", name="uq_itinerary_trip_version"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
    )

    # Create itinerary_stops table
    op.create_table(
        "itinerary_stops",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("itinerary_id", sa.Integer(), nullable=False, index=True),
        sa.Column("destination_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("planned_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_departure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visit_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("estimated_travel_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("estimated_travel_distance_km", sa.Float(), nullable=True),
        sa.Column("travel_mode", sa.String(length=50), nullable=True),
        sa.Column("selection_reason", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("estimated_cost_currency", sa.String(length=3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
    )

    # Create feedbacks table
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("destination_id", sa.Integer(), nullable=True, index=True),
        sa.Column("trip_id", sa.Integer(), nullable=True, index=True),
        sa.Column("feedback_type", sa.Enum("rating", "review", "suggestion", "bug_report", "other", name="feedbacktype"), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def downgrade():
    """Drop all tables and enum types."""
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table("feedbacks")
    op.drop_table("itinerary_stops")
    op.drop_table("itineraries")
    op.drop_table("trips")
    op.drop_table("destination_sources")
    op.drop_table("destinations")
    op.drop_table("sessions")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS feedbacktype CASCADE")
    op.execute("DROP TYPE IF EXISTS itinerarystatus CASCADE")
    op.execute("DROP TYPE IF EXISTS budgetlevel CASCADE")
    op.execute("DROP TYPE IF EXISTS transportmode CASCADE")
    op.execute("DROP TYPE IF EXISTS tripstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS accessibilitylevel CASCADE")
    op.execute("DROP TYPE IF EXISTS destinationsourcestatus CASCADE")
    op.execute("DROP TYPE IF EXISTS destinationcategory CASCADE")
    op.execute("DROP TYPE IF EXISTS sessionstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS userstatus CASCADE")

    # Drop spatial index
    op.execute("DROP INDEX IF EXISTS idx_destinations_location CASCADE")

    # Drop PostGIS extensions
    op.execute("DROP EXTENSION IF EXISTS postgis_topology CASCADE")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
