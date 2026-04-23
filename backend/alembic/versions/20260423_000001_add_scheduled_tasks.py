"""Add scheduled_tasks table

Revision ID: 7a3f2e1d4c8b
Revises: 006_asset_execution_linkage
Create Date: 2026-04-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "7a3f2e1d4c8b"
down_revision = "006_asset_execution_linkage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("schedule_type", sa.String(length=16), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("cron_expression", sa.String(length=64), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=16), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheduled_tasks_asset_id"), "scheduled_tasks", ["asset_id"], unique=False)
    op.create_index(op.f("ix_scheduled_tasks_task_type"), "scheduled_tasks", ["task_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_tasks_task_type"), table_name="scheduled_tasks")
    op.drop_index(op.f("ix_scheduled_tasks_asset_id"), table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
