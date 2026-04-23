from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.port_scans.models import PortScan


class PortScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        asset_id: int | None,
        ip: str,
        success: bool,
        message: str,
        checked_ports: list[int],
        open_ports: list[dict],
    ) -> PortScan:
        scan = PortScan(
            asset_id=asset_id,
            ip=ip,
            success=success,
            message=message,
            checked_ports=checked_ports,
            open_ports=open_ports,
        )
        self.session.add(scan)
        await self.session.flush()
        await self.session.refresh(scan)
        return scan

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[PortScan]:
        result = await self.session.execute(
            select(PortScan).order_by(PortScan.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())
