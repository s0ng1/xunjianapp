"""Add daily focus item states

Revision ID: 20260411_000005
Revises: 20260410_000004
Create Date: 2026-04-11 00:00:05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260411_000005"
down_revision: Union[str, None] = "20260410_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_focus_item_states",
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("item_id"),
    )
    op.create_index(
        "ix_daily_focus_item_states_reference_date",
        "daily_focus_item_states",
        ["reference_date"],
        unique=False,
    )
    op.create_index(
        "ix_daily_focus_item_states_status",
        "daily_focus_item_states",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_focus_item_states_status", table_name="daily_focus_item_states")
    op.drop_index("ix_daily_focus_item_states_reference_date", table_name="daily_focus_item_states")
    op.drop_table("daily_focus_item_states")
