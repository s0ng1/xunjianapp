from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BaselineRuleDefinition(BaseModel):
    rule_id: str
    name: str
    device_type: str
    risk_level: str
    check_method: str
    judge_logic: str
    matcher: dict
    remediation: str


class BaselineCheckWrite(BaseModel):
    rule_id: str
    rule_name: str
    device_type: str
    category: str = "other"
    risk_level: str
    check_type: str = "auto"
    check_method: str
    judge_logic: str
    remediation: str
    status: str = Field(..., pattern="^(pass|fail|unknown|not_applicable)$")
    detail: str
    evidence: str = ""
    manual_check_hint: str | None = None
    raw_matcher: dict = Field(default_factory=dict)


class BaselineCheckRead(BaseModel):
    rule_id: str
    rule_name: str
    device_type: str
    category: str = "other"
    risk_level: str
    check_type: str = "auto"
    check_method: str
    judge_logic: str
    remediation: str
    status: str = Field(..., pattern="^(pass|fail|unknown|not_applicable)$")
    detail: str
    evidence: str = ""
    manual_check_hint: str | None = None


BaselineSourceType = Literal["linux_inspection", "switch_inspection"]


class BaselineRunRead(BaseModel):
    asset_id: int | None = None
    inspection_id: int
    source_type: BaselineSourceType
    device_type: str
    ip: str
    username: str
    vendor: str | None = None
    success: bool
    message: str
    baseline_results: list[BaselineCheckRead] = Field(default_factory=list)
    created_at: datetime
