from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.switch_inspections.models import SwitchInspection


class SwitchInspectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        asset_id: int | None,
        ip: str,
        username: str,
        vendor: str,
        success: bool,
        message: str,
        raw_config: str | None,
    ) -> SwitchInspection:
        inspection = SwitchInspection(
            asset_id=asset_id,
            ip=ip,
            username=username,
            vendor=vendor,
            success=success,
            message=message,
            raw_config=raw_config,
        )
        self.session.add(inspection)
        await self.session.flush()
        await self.session.refresh(inspection)
        return inspection

    async def list_all(
        self,
        *,
        vendor: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SwitchInspection]:
        statement = select(SwitchInspection)
        if vendor is not None:
            statement = statement.where(SwitchInspection.vendor == vendor)
        result = await self.session.execute(
            statement.order_by(SwitchInspection.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, inspection_id: int) -> SwitchInspection | None:
        return await self.session.get(SwitchInspection, inspection_id)
