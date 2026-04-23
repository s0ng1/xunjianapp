from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.linux_inspections.models import LinuxInspection


class LinuxInspectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        asset_id: int | None,
        ip: str,
        username: str,
        success: bool,
        message: str,
        open_ports: dict | None,
        ssh_config: dict | None,
        firewall_status: dict | None,
        time_sync_status: dict | None,
        auditd_status: dict | None,
        collected_data: dict | None,
    ) -> LinuxInspection:
        inspection = LinuxInspection(
            asset_id=asset_id,
            ip=ip,
            username=username,
            success=success,
            message=message,
            open_ports=open_ports,
            ssh_config=ssh_config,
            firewall_status=firewall_status,
            time_sync_status=time_sync_status,
            auditd_status=auditd_status,
            collected_data=collected_data,
        )
        self.session.add(inspection)
        await self.session.flush()
        await self.session.refresh(inspection)
        return inspection

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[LinuxInspection]:
        result = await self.session.execute(
            select(LinuxInspection).order_by(LinuxInspection.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, inspection_id: int) -> LinuxInspection | None:
        return await self.session.get(LinuxInspection, inspection_id)
