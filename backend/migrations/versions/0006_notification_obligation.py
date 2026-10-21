"""Persist DOWN eligibility without replaying terminal or legacy notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notification_deliveries",
        sa.Column("down_eligible_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_deliveries",
        sa.Column("down_required", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("notification_deliveries", "down_required")
    op.drop_column("notification_deliveries", "down_eligible_at")
