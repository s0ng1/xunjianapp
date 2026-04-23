from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, IPvAnyAddress, SecretStr, field_validator

from app.features.baseline.schemas import BaselineCheckRead


SwitchVendor = Literal["h3c"]


class _BaseSwitchInspectionRequest(BaseModel):
    ip: IPvAnyAddress = Field(..., examples=["192.168.1.2"], description="Target H3C switch IP.")
    username: str = Field(..., min_length=1, max_length=64, examples=["admin"])
    password: SecretStr = Field(..., min_length=1, max_length=256, examples=["change_me"])

    @field_validator("ip", mode="before")
    @classmethod
    def validate_ip(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class SwitchInspectionRequest(_BaseSwitchInspectionRequest):
    vendor: SwitchVendor = Field(..., examples=["h3c"], description="Switch vendor identifier.")


class H3CInspectionRequest(_BaseSwitchInspectionRequest):
    pass


class SwitchInspectionResponse(BaseModel):
    id: int
    asset_id: int | None = None
    ip: str
    username: str
    success: bool = Field(..., description="Whether the switch inspection succeeded.")
    vendor: str = Field(default="H3C", description="Switch vendor.")
    message: str = Field(..., description="Human-readable inspection result.")
    raw_config: str | None = Field(default=None, description="Original configuration text returned by the switch.")
    baseline_results: list[BaselineCheckRead] = Field(default_factory=list)
    created_at: datetime


H3CInspectionResponse = SwitchInspectionResponse
