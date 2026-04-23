"""Add port scans

Revision ID: 20260410_000003
Revises: 20260409_000002
Create Date: 2026-04-10 00:00:03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260410_000003"
down_revision: Union[str, None] = "20260409_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "port_scans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("checked_ports", sa.JSON(), nullable=False),
        sa.Column("open_ports", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_port_scans_ip"), "port_scans", ["ip"], unique=False)
    op.create_index("ix_port_scans_ip_created_at", "port_scans", ["ip", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_port_scans_ip_created_at", table_name="port_scans")
    op.drop_index(op.f("ix_port_scans_ip"), table_name="port_scans")
    op.drop_table("port_scans")
