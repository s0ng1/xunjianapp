from pydantic import BaseModel, Field, IPvAnyAddress, SecretStr, field_validator


class SSHTestRequest(BaseModel):
    ip: IPvAnyAddress = Field(..., examples=["192.168.1.10"], description="Target asset IP address.")
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


class SSHTestResponse(BaseModel):
    success: bool = Field(..., description="Whether the SSH login succeeded.")
    message: str = Field(..., description="Human-readable connection result.")
