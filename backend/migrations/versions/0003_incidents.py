"""Persist confirmed incidents; never invent historical events for existing DOWN rows."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Uuid(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("recovered_at", sa.DateTime(timezone=True)),
        sa.Column("closure_reason", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("closed_at IS NULL OR closed_at >= opened_at"),
        sa.CheckConstraint("recovered_at IS NULL OR recovered_at = closed_at"),
        sa.CheckConstraint("(closed_at IS NULL) = (closure_reason IS NULL)"),
        sa.CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ('RECOVERED','PAUSED','CONFIG_CHANGED')"
        ),
        sa.CheckConstraint(
            "(recovered_at IS NOT NULL) = (closure_reason IS NOT DISTINCT FROM 'RECOVERED')"
        ),
    )
    op.create_index(
        "uq_incidents_open_monitor",
        "incidents",
        ["monitor_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )
    op.create_index("ix_incidents_monitor_time", "incidents", ["monitor_id", "opened_at", "id"])
    op.create_index("ix_incidents_time", "incidents", ["opened_at", "id"])


def downgrade():
    op.drop_table("incidents")
