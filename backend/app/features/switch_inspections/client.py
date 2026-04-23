from __future__ import annotations

from dataclasses import dataclass
import logging

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

H3C_DISABLE_PAGING_COMMAND = "screen-length disable"
H3C_SHOW_CONFIG_COMMAND = "display current-configuration"

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SwitchInspectionResult:
    success: bool
    message: str
    raw_config: str | None = None


class H3CSwitchInspectorClient:
    def __init__(self, connection_timeout_seconds: int = 10, command_read_timeout_seconds: int = 120) -> None:
        self.connection_timeout_seconds = connection_timeout_seconds
        self.command_read_timeout_seconds = command_read_timeout_seconds

    def inspect(self, *, ip: str, username: str, password: str, port: int = 22) -> SwitchInspectionResult:
        connection = None
        try:
            connection = ConnectHandler(
                device_type="hp_comware",
                host=ip,
                port=port,
                username=username,
                password=password,
                conn_timeout=self.connection_timeout_seconds,
                auth_timeout=self.connection_timeout_seconds,
                banner_timeout=self.connection_timeout_seconds,
                timeout=self.connection_timeout_seconds,
                session_timeout=self.connection_timeout_seconds,
                fast_cli=False,
            )
            connection.send_command(
                H3C_DISABLE_PAGING_COMMAND,
                strip_prompt=True,
                strip_command=True,
                read_timeout=self.command_read_timeout_seconds,
            )
            raw_config = connection.send_command(
                H3C_SHOW_CONFIG_COMMAND,
                strip_prompt=True,
                strip_command=True,
                read_timeout=self.command_read_timeout_seconds,
            )
            return SwitchInspectionResult(
                success=True,
                message="H3C switch inspection completed",
                raw_config=raw_config.strip(),
            )
        except NetmikoAuthenticationException:
            return SwitchInspectionResult(success=False, message="SSH authentication failed")
        except NetmikoTimeoutException:
            return SwitchInspectionResult(success=False, message="SSH connection timed out")
        except Exception as exc:
            logger.exception(
                "Unexpected H3C switch inspection error ip=%s username=%s error_type=%s",
                ip,
                username,
                type(exc).__name__,
            )
            return SwitchInspectionResult(success=False, message="H3C switch inspection failed")
        finally:
            if connection is not None:
                connection.disconnect()
