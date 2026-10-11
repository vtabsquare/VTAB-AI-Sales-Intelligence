"""web agent control center and source health

Revision ID: 0006_web_agent_control_center
Revises: 0005_autonomous_web_agent
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_web_agent_control_center"
down_revision = "0005_autonomous_web_agent"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("web_sources", sa.Column("health_status", sa.String(40), nullable=False, server_default="READY"))
    op.add_column("web_sources", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("web_sources", sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("web_sources", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "web_agent_settings",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("browser_concurrency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_pages_per_source", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("auto_qualification", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_research", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_draft", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("auto_send", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("INSERT INTO web_agent_settings (id, enabled, browser_concurrency, max_pages_per_source, retry_count, timeout_seconds, auto_qualification, auto_research, auto_draft, auto_send) VALUES ('default', true, 1, 4, 1, 45, true, true, true, false)")


def downgrade():
    op.drop_table("web_agent_settings")
    op.drop_column("web_sources", "updated_at")
    op.drop_column("web_sources", "last_error_at")
    op.drop_column("web_sources", "last_error")
    op.drop_column("web_sources", "health_status")
