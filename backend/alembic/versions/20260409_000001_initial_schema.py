"""Initial schema

Revision ID: 20260409_000001
Revises:
Create Date: 2026-04-09 00:00:01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260409_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip", name="uq_assets_ip"),
    )
    op.create_index(op.f("ix_assets_ip"), "assets", ["ip"], unique=False)
    op.create_index(op.f("ix_assets_name"), "assets", ["name"], unique=False)
    op.create_index(op.f("ix_assets_asset_type"), "assets", ["asset_type"], unique=False)

    op.create_table(
        "linux_inspections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("open_ports", sa.JSON(), nullable=True),
        sa.Column("ssh_config", sa.JSON(), nullable=True),
        sa.Column("firewall_status", sa.JSON(), nullable=True),
        sa.Column("time_sync_status", sa.JSON(), nullable=True),
        sa.Column("auditd_status", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_linux_inspections_ip"), "linux_inspections", ["ip"], unique=False)

    op.create_table(
        "switch_inspections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("vendor", sa.String(length=32), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("raw_config", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_switch_inspections_ip"), "switch_inspections", ["ip"], unique=False)
    op.create_index(op.f("ix_switch_inspections_vendor"), "switch_inspections", ["vendor"], unique=False)

    op.create_table(
        "baseline_check_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("linux_inspection_id", sa.Integer(), nullable=True),
        sa.Column("switch_inspection_id", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("check_method", sa.String(length=64), nullable=False),
        sa.Column("judge_logic", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("raw_matcher", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["linux_inspection_id"], ["linux_inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["switch_inspection_id"], ["switch_inspections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_baseline_check_results_linux_inspection_id"),
        "baseline_check_results",
        ["linux_inspection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_baseline_check_results_switch_inspection_id"),
        "baseline_check_results",
        ["switch_inspection_id"],
        unique=False,
    )
    op.create_index(op.f("ix_baseline_check_results_rule_id"), "baseline_check_results", ["rule_id"], unique=False)
    op.create_index(
        op.f("ix_baseline_check_results_device_type"),
        "baseline_check_results",
        ["device_type"],
        unique=False,
    )
    op.create_index(op.f("ix_baseline_check_results_status"), "baseline_check_results", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_baseline_check_results_status"), table_name="baseline_check_results")
    op.drop_index(op.f("ix_baseline_check_results_device_type"), table_name="baseline_check_results")
    op.drop_index(op.f("ix_baseline_check_results_rule_id"), table_name="baseline_check_results")
    op.drop_index(op.f("ix_baseline_check_results_switch_inspection_id"), table_name="baseline_check_results")
    op.drop_index(op.f("ix_baseline_check_results_linux_inspection_id"), table_name="baseline_check_results")
    op.drop_table("baseline_check_results")

    op.drop_index(op.f("ix_switch_inspections_vendor"), table_name="switch_inspections")
    op.drop_index(op.f("ix_switch_inspections_ip"), table_name="switch_inspections")
    op.drop_table("switch_inspections")

    op.drop_index(op.f("ix_linux_inspections_ip"), table_name="linux_inspections")
    op.drop_table("linux_inspections")

    op.drop_index(op.f("ix_assets_asset_type"), table_name="assets")
    op.drop_index(op.f("ix_assets_name"), table_name="assets")
    op.drop_index(op.f("ix_assets_ip"), table_name="assets")
    op.drop_table("assets")
