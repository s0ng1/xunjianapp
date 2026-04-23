from datetime import date

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.features.assets.router import get_asset_service
from app.features.assets.service import AssetService
from app.features.daily_focus.repository import DailyFocusItemStateRepository
from app.features.daily_focus.schemas import DailyFocusItemStateRead, DailyFocusItemStateUpdate, DailyFocusRead
from app.features.daily_focus.service import DailyFocusService
from app.features.linux_inspections.router import get_linux_inspection_service
from app.features.linux_inspections.service import LinuxInspectionService

router = APIRouter(prefix="/daily-focus")


def get_daily_focus_service(
    session: AsyncSession = Depends(get_db_session),
    asset_service: AssetService = Depends(get_asset_service),
    linux_inspection_service: LinuxInspectionService = Depends(get_linux_inspection_service),
) -> DailyFocusService:
    return DailyFocusService(
        state_repository=DailyFocusItemStateRepository(session),
        asset_service=asset_service,
        linux_inspection_service=linux_inspection_service,
    )


@router.get(
    "",
    response_model=DailyFocusRead,
    summary="Get daily focus view",
    description="Aggregate Linux inspection and baseline results into today's operational priorities.",
)
async def get_daily_focus(
    reference_date: date | None = Query(default=None),
    service: DailyFocusService = Depends(get_daily_focus_service),
) -> DailyFocusRead:
    return await service.get_daily_focus(reference_date=reference_date)


@router.patch(
    "/items/{item_id}",
    response_model=DailyFocusItemStateRead,
    summary="Update daily focus item state",
    description="Persist the processing status and remark for a daily focus item under a specific reference date.",
)
async def update_daily_focus_item_state(
    item_id: str = Path(..., min_length=8, max_length=64),
    payload: DailyFocusItemStateUpdate = ...,
    service: DailyFocusService = Depends(get_daily_focus_service),
) -> DailyFocusItemStateRead:
    return await service.update_item_state(item_id=item_id, payload=payload)
