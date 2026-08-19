"""add versioned workflow snapshots

Revision ID: 0005_generic_workflows
Revises: 0004_runtime_llm_and_resume
Create Date: 2026-08-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_generic_workflows"
down_revision: Union[str, None] = "0004_runtime_llm_and_resume"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("workflow_version", sa.Text(), nullable=False, server_default="1.0.0"),
    )
    op.add_column("jobs", sa.Column("workflow_schema_hash", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("workflow_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column("jobs", "workflow_version", server_default=None)


def downgrade() -> None:
    op.drop_column("jobs", "workflow_snapshot")
    op.drop_column("jobs", "workflow_schema_hash")
    op.drop_column("jobs", "workflow_version")
