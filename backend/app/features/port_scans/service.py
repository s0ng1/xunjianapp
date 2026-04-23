from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assets.repository import AssetRepository
from app.features.port_scans.client import PortScanExecution, PortScanner
from app.features.port_scans.repository import PortScanRepository
from app.features.port_scans.schemas import PortScanRead, PortScanRequest

logger = logging.getLogger(__name__)


class PortScanService:
    def __init__(
        self,
        session: AsyncSession,
        scanner: PortScanner,
    ) -> None:
        self.session = session
        self.repository = PortScanRepository(session)
        self.asset_repository = AssetRepository(session)
        self.scanner = scanner

    async def run_scan(self, payload: PortScanRequest) -> PortScanRead:
        return await self.run_scan_for_target(ip=str(payload.ip), ports=payload.ports or None)

    async def run_scan_for_target(
        self,
        *,
        ip: str,
        ports: list[int] | None = None,
        asset_id: int | None = None,
    ) -> PortScanRead:
        execution = await self.scanner.scan(
            ip=ip,
            ports=ports,
        )
        self._log_result(ip=ip, execution=execution)
        try:
            resolved_asset_id = asset_id if asset_id is not None else await self._resolve_asset_id(ip)
            scan = await self.repository.add(
                asset_id=resolved_asset_id,
                ip=ip,
                success=execution.success,
                message=execution.message,
                checked_ports=execution.checked_ports,
                open_ports=[item.model_dump() for item in execution.open_ports],
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return self._to_read_model(scan)

    async def list_scans(self, *, skip: int = 0, limit: int = 100) -> list[PortScanRead]:
        scans = await self.repository.list_all(skip=skip, limit=limit)
        return [self._to_read_model(scan) for scan in scans]

    def _to_read_model(self, scan) -> PortScanRead:
        return PortScanRead(
            id=scan.id,
            asset_id=scan.asset_id,
            ip=scan.ip,
            success=scan.success,
            message=scan.message,
            checked_ports=list(scan.checked_ports),
            open_ports=list(scan.open_ports),
            created_at=scan.created_at,
        )

    async def _resolve_asset_id(self, ip: str) -> int | None:
        asset = await self.asset_repository.get_by_ip(ip)
        return asset.id if asset is not None else None

    def _log_result(self, *, ip: str, execution: PortScanExecution) -> None:
        level = logging.INFO if execution.success else logging.WARNING
        logger.log(
            level,
            "Port scan finished ip=%s success=%s checked_ports=%s open_count=%s message=%s",
            ip,
            execution.success,
            execution.checked_ports,
            len(execution.open_ports),
            execution.message,
        )
