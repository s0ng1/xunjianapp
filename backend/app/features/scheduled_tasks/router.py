from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.features.scheduled_tasks.schemas import (
    ScheduledTaskCreate,
    ScheduledTaskRead,
    ScheduledTaskTriggerResponse,
    ScheduledTaskUpdate,
)
from app.features.scheduled_tasks.service import ScheduledTaskService

router = APIRouter(prefix="/scheduled-tasks", tags=["scheduled-tasks"])


def get_scheduler_manager():
    from app.main import scheduler_manager

    return scheduler_manager


def get_scheduled_task_service(
    session: AsyncSession = Depends(get_db_session),
) -> ScheduledTaskService:
    from app.main import scheduler_manager

    return ScheduledTaskService(session, scheduler_manager)


@router.post(
    "",
    response_model=ScheduledTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled task",
)
async def create_scheduled_task(
    payload: ScheduledTaskCreate,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> ScheduledTaskRead:
    return await service.create(payload)


@router.get("", response_model=list[ScheduledTaskRead], summary="List scheduled tasks")
async def list_scheduled_tasks(
    task_type: str | None = Query(None),
    asset_id: int | None = Query(None),
    is_enabled: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> list[ScheduledTaskRead]:
    return await service.list(
        task_type=task_type,
        asset_id=asset_id,
        is_enabled=is_enabled,
        skip=skip,
        limit=limit,
    )


@router.get("/{task_id}", response_model=ScheduledTaskRead, summary="Get a scheduled task")
async def get_scheduled_task(
    task_id: int,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> ScheduledTaskRead:
    return await service.get(task_id)


@router.patch("/{task_id}", response_model=ScheduledTaskRead, summary="Update a scheduled task")
async def update_scheduled_task(
    task_id: int,
    payload: ScheduledTaskUpdate,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> ScheduledTaskRead:
    return await service.update(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a scheduled task")
async def delete_scheduled_task(
    task_id: int,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> None:
    await service.delete(task_id)


@router.post(
    "/{task_id}/trigger",
    response_model=ScheduledTaskTriggerResponse,
    summary="Trigger a scheduled task immediately",
)
async def trigger_scheduled_task(
    task_id: int,
    service: ScheduledTaskService = Depends(get_scheduled_task_service),
) -> ScheduledTaskTriggerResponse:
    return await service.trigger(task_id)
