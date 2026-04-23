from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import socket

from app.features.port_scans.schemas import PortScanPortState

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PortScanExecution:
    success: bool
    message: str
    checked_ports: list[int]
    open_ports: list[PortScanPortState]


class PortScanner:
    def __init__(
        self,
        timeout_seconds: int = 1,
        default_ports: list[int] | None = None,
        max_concurrency: int = 50,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.default_ports = list(default_ports or [22, 80, 443])
        self.max_concurrency = max_concurrency

    async def scan(self, *, ip: str, ports: list[int] | None = None) -> PortScanExecution:
        checked_ports = list(ports) if ports else list(self.default_ports)
        open_ports: list[PortScanPortState] = []

        try:
            semaphore = asyncio.Semaphore(self.max_concurrency)

            async def check_port(port: int) -> tuple[int, bool]:
                async with semaphore:
                    is_open = await asyncio.to_thread(self._is_port_open, ip=ip, port=port)
                    return port, is_open

            results = await asyncio.gather(*(check_port(port) for port in checked_ports))
            open_ports = [
                PortScanPortState(port=port, is_open=True)
                for port, is_open in results
                if is_open
            ]
        except Exception as exc:
            logger.exception(
                "Unexpected port scan error ip=%s error_type=%s",
                ip,
                type(exc).__name__,
            )
            return PortScanExecution(
                success=False,
                message="Port scan failed",
                checked_ports=checked_ports,
                open_ports=[],
            )

        return PortScanExecution(
            success=True,
            message=f"Port scan completed: {len(open_ports)} open of {len(checked_ports)} checked",
            checked_ports=checked_ports,
            open_ports=open_ports,
        )

    def _is_port_open(self, *, ip: str, port: int) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=self.timeout_seconds):
                return True
        except OSError:
            return False
