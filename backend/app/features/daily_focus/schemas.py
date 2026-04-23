from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


DailyFocusSection = Literal["today_must_handle", "today_changes", "weekly_plan"]
DailyFocusItemStatus = Literal[
    "pending",
    "in_progress",
    "resolved",
    "ignored",
    "needs_manual_confirmation",
]


class DailyFocusItemRead(BaseModel):
    id: str
    asset_id: int | None = None
    asset_name: str
    asset_ip: str
    section: DailyFocusSection
    priority_rank: int = Field(..., ge=1, le=5)
    severity: str
    headline: str
    summary: str
    detected_at: datetime
    source_type: str
    rule_id: str | None = None
    persistent_days: int = 0
    status: DailyFocusItemStatus = "pending"
    remark: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None


class DailyFocusAssetGroupRead(BaseModel):
    asset_id: int | None = None
    asset_name: str
    asset_ip: str
    items: list[DailyFocusItemRead] = Field(default_factory=list)


class DailyFocusSummaryRead(BaseModel):
    must_handle_count: int = 0
    today_changes_count: int = 0
    weekly_plan_count: int = 0


class DailyFocusPriorityDeviceRead(BaseModel):
    asset_id: int | None = None
    asset_name: str
    asset_ip: str
    high_count: int = 0
    medium_count: int = 0
    today_changes_count: int = 0
    needs_manual_confirmation_count: int = 0


class DailyFocusItemStateRead(BaseModel):
    item_id: str
    reference_date: date
    status: DailyFocusItemStatus
    remark: str | None = None
    updated_at: datetime
    updated_by: str


class DailyFocusItemStateUpdate(BaseModel):
    reference_date: date
    status: DailyFocusItemStatus
    remark: str | None = None
    updated_by: str = "local-operator"


class DailyFocusRead(BaseModel):
    reference_date: date
    generated_at: datetime
    today_summary: str
    summary: DailyFocusSummaryRead
    priority_devices: list[DailyFocusPriorityDeviceRead] = Field(default_factory=list)
    today_must_handle: list[DailyFocusAssetGroupRead] = Field(default_factory=list)
    today_changes: list[DailyFocusItemRead] = Field(default_factory=list)
    weekly_plan: list[DailyFocusItemRead] = Field(default_factory=list)
