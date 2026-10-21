"""Versioned monitor configuration and normalized groups. Existing observations retained."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "monitors", sa.Column("config_version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "monitors",
        sa.Column("run_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint("ck_monitors_version", "monitors", "config_version >= 1")
    op.add_column(
        "check_results",
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("config_version >= 1"),
    )
    op.create_table(
        "monitor_groups",
        sa.Column(
            "group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column(
            "monitor_id",
            sa.Uuid(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_monitor_groups_monitor_id", "monitor_groups", ["monitor_id"])
    op.create_table(
        "group_recipients",
        sa.Column(
            "group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("email", sa.String(254), primary_key=True),
    )


def downgrade():
    op.drop_table("group_recipients")
    op.drop_table("monitor_groups")
    op.drop_table("groups")
    op.drop_column("check_results", "config_version")
    op.drop_constraint("ck_monitors_version", "monitors")
    op.drop_column("monitors", "run_requested")
    op.drop_column("monitors", "config_version")
