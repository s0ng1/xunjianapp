from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Security Inspection Platform"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://sec_user:change_me@db:5432/sec"
    allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )
    db_schema_init_mode: Literal["auto", "create_all", "migrations"] = "auto"
    ssh_connection_timeout_seconds: int = Field(default=10, ge=1)
    ssh_command_read_timeout_seconds: int = Field(default=120, ge=1)
    port_scan_connect_timeout_seconds: int = Field(default=1, ge=1)
    port_scan_default_ports: str = Field(default="22,80,443")
    ssh_test_rate_limit: str = Field(default="5/minute")
    linux_inspection_rate_limit: str = Field(default="10/minute")
    switch_inspection_rate_limit: str = Field(default="10/minute")
    port_scan_rate_limit: str = Field(default="20/minute")
    credential_encryption_key: str = Field(default="local-dev-only-encryption-key")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def should_create_tables(self) -> bool:
        if self.db_schema_init_mode == "create_all":
            return True
        if self.db_schema_init_mode == "migrations":
            return False
        return self.environment.lower() == "development"

    @property
    def parsed_port_scan_default_ports(self) -> list[int]:
        ports: list[int] = []
        for value in self.port_scan_default_ports.split(","):
            cleaned = value.strip()
            if not cleaned:
                continue
            port = int(cleaned)
            if port < 1 or port > 65535:
                raise ValueError(f"Invalid port in PORT_SCAN_DEFAULT_PORTS: {cleaned}")
            if port not in ports:
                ports.append(port)
        return ports


@lru_cache
def get_settings() -> Settings:
    return Settings()
