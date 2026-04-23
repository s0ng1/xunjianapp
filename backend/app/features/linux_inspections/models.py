from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LinuxInspection(Base):
    __tablename__ = "linux_inspections"
    __table_args__ = (
        Index("ix_linux_inspections_ip_created_at", "ip", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ip: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    open_ports: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ssh_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    firewall_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    time_sync_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    auditd_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    collected_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
