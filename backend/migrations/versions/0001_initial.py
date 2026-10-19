"""Initial monitoring and observation schema.

Revision ID: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("expected_status", sa.Integer(), nullable=False),
        sa.Column("expected_body", sa.String(1000)),
        sa.Column("failure_threshold", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(10), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_status_code", sa.Integer()),
        sa.Column("last_response_ms", sa.Float()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint("interval_seconds BETWEEN 30 AND 3600"),
        sa.CheckConstraint("timeout_seconds BETWEEN 0.1 AND 120"),
        sa.CheckConstraint("expected_status BETWEEN 100 AND 599"),
        sa.CheckConstraint("failure_threshold BETWEEN 1 AND 10"),
        sa.CheckConstraint("state IN ('UNKNOWN','UP','DOWN','PAUSED')"),
        sa.CheckConstraint("consecutive_failures >= 0"),
        sa.CheckConstraint("(lease_token IS NULL) = (lease_until IS NULL)"),
    )
    op.create_index("ix_monitors_next_due_at", "monitors", ["next_due_at"])
    op.create_table(
        "check_results",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Uuid(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer()),
        sa.Column("response_ms", sa.Float(), nullable=False),
        sa.Column("error", sa.Text()),
    )
    op.create_index("ix_results_monitor_time", "check_results", ["monitor_id", "checked_at"])


def downgrade():
    op.drop_table("check_results")
    op.drop_table("monitors")
