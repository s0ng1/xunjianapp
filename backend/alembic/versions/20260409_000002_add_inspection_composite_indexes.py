"""Add inspection composite indexes

Revision ID: 20260409_000002
Revises: 20260409_000001
Create Date: 2026-04-09 00:00:02

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260409_000002"
down_revision: Union[str, None] = "20260409_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_linux_inspections_ip_created_at",
        "linux_inspections",
        ["ip", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_switch_inspections_ip_created_at",
        "switch_inspections",
        ["ip", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_switch_inspections_ip_created_at", table_name="switch_inspections")
    op.drop_index("ix_linux_inspections_ip_created_at", table_name="linux_inspections")
