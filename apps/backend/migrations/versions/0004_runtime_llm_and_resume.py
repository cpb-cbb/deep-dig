"""add runtime LLM settings and resumable item claims

Revision ID: 0004_runtime_llm_and_resume
Revises: 0003_remove_user_limits
Create Date: 2026-08-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_runtime_llm_and_resume"
down_revision: Union[str, None] = "0003_remove_user_limits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("llm_provider", sa.Text(), nullable=True))
    op.add_column("user_settings", sa.Column("llm_base_url", sa.Text(), nullable=True))
    op.add_column("user_settings", sa.Column("llm_model", sa.Text(), nullable=True))
    op.add_column(
        "user_settings", sa.Column("llm_api_key_encrypted", sa.Text(), nullable=True)
    )
    op.add_column("user_settings", sa.Column("llm_temperature", sa.Float(), nullable=True))
    op.add_column("job_items", sa.Column("claim_token", sa.Text(), nullable=True))
    op.add_column(
        "job_items", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("job_items", "claimed_at")
    op.drop_column("job_items", "claim_token")
    op.drop_column("user_settings", "llm_temperature")
    op.drop_column("user_settings", "llm_api_key_encrypted")
    op.drop_column("user_settings", "llm_model")
    op.drop_column("user_settings", "llm_base_url")
    op.drop_column("user_settings", "llm_provider")
