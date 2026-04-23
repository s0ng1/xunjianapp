from datetime import datetime

from pydantic import BaseModel, Field, IPvAnyAddress, SecretStr, field_validator, model_validator


class AssetCreate(BaseModel):
    ip: IPvAnyAddress = Field(
        ...,
        examples=["192.168.1.10"],
        description="Asset IP address.",
    )
    type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        examples=["linux"],
        description="Extensible asset type label, for example linux or switch.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["prod-web-01"],
        description="Readable asset name.",
    )
    connection_type: str = Field(
        default="ssh",
        min_length=1,
        max_length=32,
        description="Connection type used by the asset execution flow.",
    )
    port: int = Field(default=22, ge=1, le=65535, description="Target SSH or service port.")
    username: str | None = Field(default=None, min_length=1, max_length=64, examples=["root"])
    vendor: str | None = Field(default=None, min_length=1, max_length=32, examples=["h3c"])
    credential_password: SecretStr | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Optional password stored through the credential vault layer.",
    )
    is_enabled: bool = Field(default=True, description="Whether the asset is enabled for execution.")

    @field_validator("ip", mode="before")
    @classmethod
    def validate_ip(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("type", "name", "connection_type", "username", "vendor")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        return value.lower()

    @field_validator("connection_type")
    @classmethod
    def normalize_connection_type(cls, value: str) -> str:
        return value.lower()

    @field_validator("vendor")
    @classmethod
    def normalize_vendor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.lower()

    @model_validator(mode="after")
    def validate_execution_config(self) -> "AssetCreate":
        if self.credential_password is not None and not self.username:
            raise ValueError("username is required when credential_password is provided")
        if self.type == "switch" and self.credential_password is not None and self.vendor is None:
            raise ValueError("vendor is required for switch assets with stored credentials")
        return self


class AssetRead(BaseModel):
    id: int
    ip: str
    type: str
    name: str
    connection_type: str
    port: int
    username: str | None = None
    vendor: str | None = None
    credential_id: int | None = None
    credential_configured: bool = False
    is_enabled: bool
    created_at: datetime


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100, examples=["prod-web-01"])
    connection_type: str | None = Field(default=None, min_length=1, max_length=32)
    port: int | None = Field(default=None, ge=1, le=65535, description="Target SSH or service port.")
    username: str | None = Field(default=None, min_length=1, max_length=64, examples=["root"])
    vendor: str | None = Field(default=None, min_length=1, max_length=32, examples=["h3c"])
    credential_password: SecretStr | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Optional password rotation for the stored credential.",
    )
    is_enabled: bool | None = Field(default=None, description="Whether the asset is enabled for execution.")

    @field_validator("name", "connection_type", "username", "vendor")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("connection_type")
    @classmethod
    def normalize_connection_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.lower()

    @field_validator("vendor")
    @classmethod
    def normalize_vendor(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.lower()


class AssetPortScanRequest(BaseModel):
    ports: list[int] = Field(
        default_factory=list,
        description="Optional list of TCP ports to check. When omitted, server-side defaults are used.",
        examples=[[22, 80, 443]],
    )

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


def build_asset_read(
    *,
    asset_id: int,
    ip: str,
    asset_type: str,
    name: str,
    connection_type: str,
    port: int,
    username: str | None,
    vendor: str | None,
    credential_id: int | None,
    is_enabled: bool,
    created_at: datetime,
) -> AssetRead:
    return AssetRead(
        id=asset_id,
        ip=ip,
        type=asset_type,
        name=name,
        connection_type=connection_type,
        port=port,
        username=username,
        vendor=vendor,
        credential_id=credential_id,
        credential_configured=credential_id is not None,
        is_enabled=is_enabled,
        created_at=created_at,
    )
