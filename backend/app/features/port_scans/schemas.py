from datetime import datetime

from pydantic import BaseModel, Field, IPvAnyAddress, field_validator


class PortScanPortState(BaseModel):
    protocol: str = "tcp"
    port: int = Field(..., ge=1, le=65535)
    is_open: bool = True


class PortScanRequest(BaseModel):
    ip: IPvAnyAddress = Field(..., examples=["192.168.1.30"], description="Target IP address.")
    ports: list[int] = Field(
        default_factory=list,
        description="Optional list of TCP ports to check. When omitted, server-side defaults are used.",
        examples=[[22, 80, 443]],
    )

    @field_validator("ip", mode="before")
    @classmethod
    def validate_ip(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, value: list[int]) -> list[int]:
        normalized: list[int] = []
        for port in value:
            if port < 1 or port > 65535:
                raise ValueError("port must be between 1 and 65535")
            if port not in normalized:
                normalized.append(port)
        return normalized


class PortScanRead(BaseModel):
    id: int
    asset_id: int | None = None
    ip: str
    success: bool
    message: str
    checked_ports: list[int]
    open_ports: list[PortScanPortState]
    created_at: datetime
