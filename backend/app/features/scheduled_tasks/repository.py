from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.scheduled_tasks.models import ScheduledTask
from app.features.scheduled_tasks.schemas import ScheduledTaskCreate, ScheduledTaskUpdate


class ScheduledTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: ScheduledTaskCreate) -> ScheduledTask:
        row = ScheduledTask(
            name=payload.name,
            task_type=payload.task_type.value,
            asset_id=payload.asset_id,
            schedule_type=payload.schedule_type.value,
            interval_seconds=payload.interval_seconds,
            cron_expression=payload.cron_expression,
            timezone=payload.timezone,
            params=payload.params.model_dump(),
            is_enabled=payload.is_enabled,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_id(self, task_id: int) -> ScheduledTask | None:
        result = await self.session.execute(select(ScheduledTask).where(ScheduledTask.id == task_id))
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        task_type: str | None = None,
        asset_id: int | None = None,
        is_enabled: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ScheduledTask]:
        query = select(ScheduledTask)
        if task_type:
            query = query.where(ScheduledTask.task_type == task_type)
        if asset_id:
            query = query.where(ScheduledTask.asset_id == asset_id)
        if is_enabled is not None:
            query = query.where(ScheduledTask.is_enabled == is_enabled)
        query = query.order_by(ScheduledTask.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, task_id: int, payload: ScheduledTaskUpdate) -> ScheduledTask | None:
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            if key == "params":
                value = payload.params.model_dump() if payload.params else {}
            setattr(task, key, value)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def delete(self, task_id: int) -> bool:
        result = await self.session.execute(delete(ScheduledTask).where(ScheduledTask.id == task_id))
        return result.rowcount > 0

    async def update_run_result(
        self,
        task_id: int,
        *,
        last_run_at,
        last_status: str,
        last_message: str,
        next_run_at=None,
    ) -> None:
        await self.session.execute(
            update(ScheduledTask)
            .where(ScheduledTask.id == task_id)
            .values(
                last_run_at=last_run_at,
                last_status=last_status,
                last_message=last_message,
                next_run_at=next_run_at,
            )
        )
        await self.session.flush()
