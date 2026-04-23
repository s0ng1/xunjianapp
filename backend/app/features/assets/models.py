from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssetCredential(Base):
    __tablename__ = "asset_credentials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("ip", name="uq_assets_ip"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=False, unique=True, index=True)
    connection_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ssh")
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    credential_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
