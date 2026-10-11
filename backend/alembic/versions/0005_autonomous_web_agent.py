"""autonomous web agent tables

Revision ID: 0005_autonomous_web_agent
Revises: 0004_sales_manager
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_autonomous_web_agent"
down_revision = "0004_sales_manager"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("web_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False, unique=True),
        sa.Column("country", sa.String(120)), sa.Column("category", sa.String(120), nullable=False, server_default="open_web"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auth_required", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("scan_frequency_minutes", sa.Integer(), nullable=False, server_default="360"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"), sa.Column("success_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("opportunities_found", sa.Integer(), nullable=False, server_default="0"), sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_scan_at", sa.DateTime(timezone=True)), sa.Column("next_scan_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("web_agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_id", sa.Integer(), sa.ForeignKey("web_sources.id")),
        sa.Column("mission", sa.Text(), nullable=False), sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("current_url", sa.String(1200)), sa.Column("current_action", sa.String(500)), sa.Column("pages_visited", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_extracted", sa.Integer(), nullable=False, server_default="0"), sa.Column("opportunities_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("screenshots_json", sa.Text()), sa.Column("error_code", sa.String(120)), sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("agent_activities",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_id", sa.Integer(), sa.ForeignKey("web_agent_runs.id")),
        sa.Column("level", sa.String(30), nullable=False, server_default="info"), sa.Column("phase", sa.String(80), nullable=False, server_default="browser"),
        sa.Column("action", sa.String(300), nullable=False), sa.Column("detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("agent_approvals",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_id", sa.Integer(), sa.ForeignKey("web_agent_runs.id")),
        sa.Column("risk", sa.String(20), nullable=False, server_default="amber"), sa.Column("action_type", sa.String(120), nullable=False),
        sa.Column("title", sa.String(300), nullable=False), sa.Column("payload_json", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("decided_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_table("agent_approvals"); op.drop_table("agent_activities"); op.drop_table("web_agent_runs"); op.drop_table("web_sources")
