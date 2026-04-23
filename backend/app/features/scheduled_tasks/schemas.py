from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class TaskType(str, Enum):
    SSH_TEST = "ssh_test"
    LINUX_INSPECTION = "linux_inspection"
    SWITCH_INSPECTION = "switch_inspection"
    PORT_SCAN = "port_scan"
    BASELINE_CHECK = "baseline_check"


class ScheduleType(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"


class ScheduledTaskParams(BaseModel):
    ports: list[int] | None = None


class ScheduledTaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    task_type: TaskType
    asset_id: int | None = None
    schedule_type: ScheduleType
    interval_seconds: int | None = Field(None, gt=0)
    cron_expression: str | None = Field(None, min_length=1, max_length=64)
    timezone: str = Field(default="Asia/Shanghai", max_length=64)
    params: ScheduledTaskParams = Field(default_factory=ScheduledTaskParams)
    is_enabled: bool = True

    @model_validator(mode="after")
    def check_schedule_fields(self):
        if self.schedule_type == ScheduleType.INTERVAL and self.interval_seconds is None:
            raise ValueError("interval_seconds required for interval schedule")
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("cron_expression required for cron schedule")
        return self


class ScheduledTaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    schedule_type: ScheduleType | None = None
    interval_seconds: int | None = Field(None, gt=0)
    cron_expression: str | None = Field(None, min_length=1, max_length=64)
    timezone: str | None = Field(None, max_length=64)
    params: ScheduledTaskParams | None = None
    is_enabled: bool | None = None

    @model_validator(mode="after")
    def check_schedule_fields(self):
        if self.schedule_type == ScheduleType.INTERVAL and self.interval_seconds is None:
            raise ValueError("interval_seconds required for interval schedule")
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("cron_expression required for cron schedule")
        return self


class ScheduledTaskRead(BaseModel):
    id: int
    name: str
    task_type: str
    asset_id: int | None
    schedule_type: str
    interval_seconds: int | None
    cron_expression: str | None
    timezone: str
    params: dict
    is_enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_status: str | None
    last_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduledTaskTriggerResponse(BaseModel):
    success: bool
    message: str
    task_id: int
