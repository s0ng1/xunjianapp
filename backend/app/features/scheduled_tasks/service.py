from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.features.scheduled_tasks.repository import ScheduledTaskRepository
from app.features.scheduled_tasks.schemas import (
    ScheduledTaskCreate,
    ScheduledTaskRead,
    ScheduledTaskTriggerResponse,
    ScheduledTaskUpdate,
)


class ScheduledTaskService:
    def __init__(self, session: AsyncSession, scheduler_manager) -> None:
        self.session = session
        self.repo = ScheduledTaskRepository(session)
        self.scheduler = scheduler_manager

    async def create(self, payload: ScheduledTaskCreate) -> ScheduledTaskRead:
        async with self.session.begin():
            task = await self.repo.create(payload)
        await self.scheduler.add_or_update_task(task)
        return ScheduledTaskRead.model_validate(task)

    async def list(
        self,
        *,
        task_type: str | None = None,
        asset_id: int | None = None,
        is_enabled: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ScheduledTaskRead]:
        tasks = await self.repo.list_all(
            task_type=task_type,
            asset_id=asset_id,
            is_enabled=is_enabled,
            skip=skip,
            limit=limit,
        )
        return [ScheduledTaskRead.model_validate(t) for t in tasks]

    async def get(self, task_id: int) -> ScheduledTaskRead:
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise AppError(message="Scheduled task not found", status_code=404, code="task_not_found")
        return ScheduledTaskRead.model_validate(task)

    async def update(self, task_id: int, payload: ScheduledTaskUpdate) -> ScheduledTaskRead:
        async with self.session.begin():
            task = await self.repo.update(task_id, payload)
            if task is None:
                raise AppError(message="Scheduled task not found", status_code=404, code="task_not_found")
        await self.scheduler.add_or_update_task(task)
        return ScheduledTaskRead.model_validate(task)

    async def delete(self, task_id: int) -> None:
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise AppError(message="Scheduled task not found", status_code=404, code="task_not_found")
        await self.scheduler.remove_task(task_id)
        async with self.session.begin():
            await self.repo.delete(task_id)

    async def trigger(self, task_id: int) -> ScheduledTaskTriggerResponse:
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise AppError(message="Scheduled task not found", status_code=404, code="task_not_found")
        await self.scheduler.trigger_now(task_id)
        return ScheduledTaskTriggerResponse(success=True, message="Task triggered", task_id=task_id)
