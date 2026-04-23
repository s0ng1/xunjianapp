from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BaselineCheckResult(Base):
    __tablename__ = "baseline_check_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    linux_inspection_id: Mapped[int | None] = mapped_column(
        ForeignKey("linux_inspections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    switch_inspection_id: Mapped[int | None] = mapped_column(
        ForeignKey("switch_inspections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="other")
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    check_type: Mapped[str] = mapped_column(String(32), nullable=False, default="auto")
    check_method: Mapped[str] = mapped_column(String(64), nullable=False)
    judge_logic: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    manual_check_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_matcher: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
