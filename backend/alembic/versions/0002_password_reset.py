"""Add time-limited password reset challenges."""
from alembic import op
import sqlalchemy as sa

revision = "0002_password_reset"
down_revision = "0001_account_profile"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "password_reset_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(256), nullable=False),
        sa.Column("reset_token_hash", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_challenges_user_id", "password_reset_challenges", ["user_id"])
    op.create_index("ix_password_reset_challenges_reset_token_hash", "password_reset_challenges", ["reset_token_hash"], unique=True)

def downgrade():
    op.drop_table("password_reset_challenges")
