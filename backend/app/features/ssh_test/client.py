from __future__ import annotations

from dataclasses import dataclass
import logging

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SSHConnectionResult:
    success: bool
    message: str


class SSHConnector:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def test_connection(self, *, ip: str, username: str, password: str, port: int = 22) -> SSHConnectionResult:
        connection = None
        try:
            connection = ConnectHandler(
                device_type="terminal_server",
                host=ip,
                port=port,
                username=username,
                password=password,
                conn_timeout=self.timeout_seconds,
                auth_timeout=self.timeout_seconds,
                banner_timeout=self.timeout_seconds,
                timeout=self.timeout_seconds,
                session_timeout=self.timeout_seconds,
                fast_cli=False,
            )
            return SSHConnectionResult(success=True, message="SSH connection succeeded")
        except NetmikoAuthenticationException:
            return SSHConnectionResult(success=False, message="SSH authentication failed")
        except NetmikoTimeoutException:
            return SSHConnectionResult(success=False, message="SSH connection timed out")
        except Exception as exc:
            logger.exception(
                "Unexpected SSH connection error ip=%s username=%s error_type=%s",
                ip,
                username,
                type(exc).__name__,
            )
            return SSHConnectionResult(success=False, message="SSH connection failed")
        finally:
            if connection is not None:
                connection.disconnect()
