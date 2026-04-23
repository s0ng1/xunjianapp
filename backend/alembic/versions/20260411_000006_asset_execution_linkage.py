"""Add asset execution linkage and credential vault

Revision ID: 20260411_000006
Revises: 20260411_000005
Create Date: 2026-04-11 00:00:06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260411_000006"
down_revision: Union[str, None] = "20260411_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("encrypted_password", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("assets", sa.Column("connection_type", sa.String(length=32), server_default="ssh", nullable=False))
    op.add_column("assets", sa.Column("port", sa.Integer(), server_default="22", nullable=False))
    op.add_column("assets", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column("assets", sa.Column("vendor", sa.String(length=32), nullable=True))
    op.add_column("assets", sa.Column("credential_id", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index(op.f("ix_assets_vendor"), "assets", ["vendor"], unique=False)
    op.create_index(op.f("ix_assets_credential_id"), "assets", ["credential_id"], unique=False)
    op.create_foreign_key(
        "fk_assets_credential_id_asset_credentials",
        "assets",
        "asset_credentials",
        ["credential_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("linux_inspections", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_linux_inspections_asset_id"), "linux_inspections", ["asset_id"], unique=False)
    op.create_foreign_key(
        "fk_linux_inspections_asset_id_assets",
        "linux_inspections",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("switch_inspections", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_switch_inspections_asset_id"), "switch_inspections", ["asset_id"], unique=False)
    op.create_foreign_key(
        "fk_switch_inspections_asset_id_assets",
        "switch_inspections",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("port_scans", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_port_scans_asset_id"), "port_scans", ["asset_id"], unique=False)
    op.create_foreign_key(
        "fk_port_scans_asset_id_assets",
        "port_scans",
        "assets",
        ["asset_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            """
            UPDATE linux_inspections
            SET asset_id = (
                SELECT assets.id
                FROM assets
                WHERE assets.ip = linux_inspections.ip
                LIMIT 1
            )
            WHERE asset_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE switch_inspections
            SET asset_id = (
                SELECT assets.id
                FROM assets
                WHERE assets.ip = switch_inspections.ip
                LIMIT 1
            )
            WHERE asset_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE port_scans
            SET asset_id = (
                SELECT assets.id
                FROM assets
                WHERE assets.ip = port_scans.ip
                LIMIT 1
            )
            WHERE asset_id IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_port_scans_asset_id_assets", "port_scans", type_="foreignkey")
    op.drop_index(op.f("ix_port_scans_asset_id"), table_name="port_scans")
    op.drop_column("port_scans", "asset_id")

    op.drop_constraint("fk_switch_inspections_asset_id_assets", "switch_inspections", type_="foreignkey")
    op.drop_index(op.f("ix_switch_inspections_asset_id"), table_name="switch_inspections")
    op.drop_column("switch_inspections", "asset_id")

    op.drop_constraint("fk_linux_inspections_asset_id_assets", "linux_inspections", type_="foreignkey")
    op.drop_index(op.f("ix_linux_inspections_asset_id"), table_name="linux_inspections")
    op.drop_column("linux_inspections", "asset_id")

    op.drop_constraint("fk_assets_credential_id_asset_credentials", "assets", type_="foreignkey")
    op.drop_index(op.f("ix_assets_credential_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_vendor"), table_name="assets")
    op.drop_column("assets", "is_enabled")
    op.drop_column("assets", "credential_id")
    op.drop_column("assets", "vendor")
    op.drop_column("assets", "username")
    op.drop_column("assets", "port")
    op.drop_column("assets", "connection_type")

    op.drop_table("asset_credentials")
