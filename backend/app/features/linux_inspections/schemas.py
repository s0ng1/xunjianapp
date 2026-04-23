from datetime import datetime

from pydantic import BaseModel, Field, IPvAnyAddress, SecretStr, field_validator

from app.features.baseline.schemas import BaselineCheckRead


class LinuxInspectionRequest(BaseModel):
    ip: IPvAnyAddress = Field(..., examples=["192.168.1.10"], description="Target Linux host IP.")
    username: str = Field(..., min_length=1, max_length=64, examples=["root"])
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


class OpenPortEntry(BaseModel):
    protocol: str
    local_address: str
    port: str
    state: str | None = None


class OpenPortsResult(BaseModel):
    ports: list[OpenPortEntry]
    raw_output: str


class SSHConfigResult(BaseModel):
    settings: dict[str, str]
    raw_output: str


class FirewallStatusResult(BaseModel):
    firewalld: str | None = None
    ufw: str | None = None
    iptables_rules: list[str] = Field(default_factory=list)
    raw_output: str


class TimeSyncStatusResult(BaseModel):
    timedatectl: str | None = None
    service_status: str | None = None
    raw_output: str


class AuditdStatusResult(BaseModel):
    service_status: str | None = None
    auditctl_status: str | None = None
    raw_output: str


class CollectedDataEntry(BaseModel):
    type: str
    command: str
    raw_output: str | None = None
    normalized_output: str | None = None
    error: str | None = None


class LinuxInspectionRead(BaseModel):
    id: int
    asset_id: int | None = None
    ip: str
    username: str
    success: bool
    message: str
    open_ports: OpenPortsResult | None = None
    ssh_config: SSHConfigResult | None = None
    firewall_status: FirewallStatusResult | None = None
    time_sync_status: TimeSyncStatusResult | None = None
    auditd_status: AuditdStatusResult | None = None
    collected_data: dict[str, CollectedDataEntry] = Field(default_factory=dict)
    baseline_results: list[BaselineCheckRead] = Field(default_factory=list)
    created_at: datetime
