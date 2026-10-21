"""Explicit publication permissions and honest observation cadence snapshots."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("check_results", sa.Column("interval_seconds", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_results_interval_snapshot", "check_results", "interval_seconds BETWEEN 30 AND 3600"
    )
    op.create_table(
        "public_pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("config_version >= 1"),
    )
    op.create_table(
        "publications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "page_id",
            sa.Uuid(),
            sa.ForeignKey("public_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "monitor_id",
            sa.Uuid(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("public_name", sa.String(120), nullable=False),
        sa.Column("show_history", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("page_id", "monitor_id"),
    )


def downgrade():
    op.drop_table("publications")
    op.drop_table("public_pages")
    op.drop_constraint("ck_results_interval_snapshot", "check_results", type_="check")
    op.drop_column("check_results", "interval_seconds")
