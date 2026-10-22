"""Add destinations, trips, and disruption recovery history."""
from alembic import op
import sqlalchemy as sa
revision = "0003_travel_mvp"
down_revision = "0002_password_reset"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("destinations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_hours", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("difficulty", sa.String(30), nullable=False, server_default="Easy"),
        sa.Column("source_label", sa.String(120), nullable=False, server_default="Simulated demonstration data"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("slug"))
    op.create_index("ix_destinations_slug", "destinations", ["slug"], unique=True)
    op.create_index("ix_destinations_name", "destinations", ["name"])
    op.create_table("trips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("start_location", sa.String(160), nullable=False),
        sa.Column("destination_id", sa.Integer(), sa.ForeignKey("destinations.id"), nullable=False),
        sa.Column("travel_date", sa.String(10), nullable=False),
        sa.Column("travellers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("budget", sa.Integer(), nullable=False),
        sa.Column("transport_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("food_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stay_cost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
        sa.Column("itinerary_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.create_table("recovery_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("disruption_type", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("original_plan_json", sa.Text(), nullable=False),
        sa.Column("revised_plan_json", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_recovery_events_trip_id", "recovery_events", ["trip_id"])
    op.create_index("ix_recovery_events_user_id", "recovery_events", ["user_id"])

def downgrade():
    op.drop_table("recovery_events")
    op.drop_table("trips")
    op.drop_table("destinations")
