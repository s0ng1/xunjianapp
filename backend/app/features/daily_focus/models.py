from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyFocusItemState(Base):
    __tablename__ = "daily_focus_item_states"
    __table_args__ = (
        Index("ix_daily_focus_item_states_reference_date", "reference_date"),
    )

    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="local-operator")
