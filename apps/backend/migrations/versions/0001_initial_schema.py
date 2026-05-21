"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("create extension if not exists pgcrypto")
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False, server_default="free"),
        sa.Column("monthly_quota", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_extractions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "user_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preferred_language", sa.Text(), nullable=False, server_default="zh"),
        sa.Column("store_raw_text", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify_on_job_complete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("telemetry_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("client_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_user_created", "jobs", ["user_id", sa.text("created_at desc")])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_hash", sa.Text(), nullable=False),
        sa.Column("text_length", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_results", postgresql.JSONB(), nullable=True),
        sa.Column("parsed_result", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("llm_tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("job_id", "ordinal", name="uq_job_items_job_ordinal"),
    )
    op.create_index("ix_job_items_job_status", "job_items", ["job_id", "status"])
    op.create_table(
        "usage_daily",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("extractions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_tokens_in", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("llm_tokens_out", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("llm_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
    )
    op.create_table(
        "abuse_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_abuse_events_user_created", "abuse_events", ["user_id", sa.text("created_at desc")])
    op.create_index("ix_abuse_events_ip_created", "abuse_events", ["ip", sa.text("created_at desc")])


def downgrade() -> None:
    op.drop_table("abuse_events")
    op.drop_table("usage_daily")
    op.drop_table("job_items")
    op.drop_table("jobs")
    op.drop_table("user_settings")
    op.drop_table("users")
