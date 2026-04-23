"""Add Linux baseline v1 fields

Revision ID: 20260410_000004
Revises: 20260410_000003
Create Date: 2026-04-10 00:00:04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260410_000004"
down_revision: Union[str, None] = "20260410_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("linux_inspections", sa.Column("collected_data", sa.JSON(), nullable=True))

    op.add_column(
        "baseline_check_results",
        sa.Column("category", sa.String(length=64), nullable=False, server_default="other"),
    )
    op.add_column(
        "baseline_check_results",
        sa.Column("check_type", sa.String(length=32), nullable=False, server_default="auto"),
    )
    op.add_column(
        "baseline_check_results",
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "baseline_check_results",
        sa.Column("manual_check_hint", sa.Text(), nullable=True),
    )

    op.alter_column("baseline_check_results", "category", server_default=None)
    op.alter_column("baseline_check_results", "check_type", server_default=None)
    op.alter_column("baseline_check_results", "evidence", server_default=None)


def downgrade() -> None:
    op.drop_column("baseline_check_results", "manual_check_hint")
    op.drop_column("baseline_check_results", "evidence")
    op.drop_column("baseline_check_results", "check_type")
    op.drop_column("baseline_check_results", "category")
    op.drop_column("linux_inspections", "collected_data")
