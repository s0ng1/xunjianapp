from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.daily_focus.models import DailyFocusItemState
from app.features.daily_focus.schemas import DailyFocusItemStateRead


class DailyFocusItemStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_reference_date(self, *, reference_date: date) -> dict[str, DailyFocusItemStateRead]:
        result = await self.session.execute(
            select(DailyFocusItemState).where(DailyFocusItemState.reference_date == reference_date)
        )
        rows = result.scalars().all()
        return {row.item_id: self._to_read_model(row) for row in rows}

    async def upsert(
        self,
        *,
        item_id: str,
        reference_date: date,
        status: str,
        remark: str | None,
        updated_by: str,
        updated_at: datetime,
    ) -> DailyFocusItemStateRead:
        row = await self.session.get(DailyFocusItemState, item_id)
        if row is None:
            row = DailyFocusItemState(
                item_id=item_id,
                reference_date=reference_date,
                status=status,
                remark=remark,
                updated_by=updated_by,
                updated_at=updated_at,
            )
            self.session.add(row)
        else:
            row.reference_date = reference_date
            row.status = status
            row.remark = remark
            row.updated_by = updated_by
            row.updated_at = updated_at
        await self.session.flush()
        await self.session.refresh(row)
        return self._to_read_model(row)

    def _to_read_model(self, row: DailyFocusItemState) -> DailyFocusItemStateRead:
        return DailyFocusItemStateRead(
            item_id=row.item_id,
            reference_date=row.reference_date,
            status=row.status,
            remark=row.remark,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )
