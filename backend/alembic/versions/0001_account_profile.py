"""Create account, verification, session and profile tables."""
from alembic import op
import sqlalchemy as sa
revision = "0001_account_profile"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("full_name", sa.String(120), nullable=False), sa.Column("username", sa.String(30), nullable=False), sa.Column("email", sa.String(254), nullable=False), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("consent", sa.Boolean(), nullable=False), sa.Column("email_verified", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("profiles", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("preferred_language", sa.String(30), nullable=False), sa.Column("city", sa.String(100)), sa.Column("region", sa.String(100)), sa.Column("travel_interests", sa.Text(), nullable=False), sa.Column("preferred_budget", sa.String(30)), sa.Column("preferred_duration_days", sa.Integer()), sa.Column("onboarding_complete", sa.Boolean(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=True)
    op.create_table("verification_challenges", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("code_hash", sa.String(256), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("used", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_verification_challenges_user_id", "verification_challenges", ["user_id"])
    op.create_table("user_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=True)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

def downgrade():
    op.drop_table("user_sessions")
    op.drop_table("verification_challenges")
    op.drop_table("profiles")
    op.drop_table("users")
