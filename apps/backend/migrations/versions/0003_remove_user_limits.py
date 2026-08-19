"""remove SaaS plan and quota fields

Revision ID: 0003_remove_user_limits
Revises: 0002_job_idempotency
Create Date: 2026-08-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_remove_user_limits"
down_revision: Union[str, None] = "0002_job_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "ban_reason")
    op.drop_column("users", "is_banned")
    op.drop_column("users", "quota_reset_at")
    op.drop_column("users", "used_this_month")
    op.drop_column("users", "monthly_quota")
    op.drop_column("users", "plan")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("plan", sa.Text(), nullable=False, server_default="free"),
    )
    op.add_column(
        "users",
        sa.Column("monthly_quota", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "users",
        sa.Column("used_this_month", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "quota_reset_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("date_trunc('month', now()) + interval '1 month'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("ban_reason", sa.Text(), nullable=True))
