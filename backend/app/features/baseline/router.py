from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.baseline.schemas import BaselineRunRead
from app.features.baseline.service import BaselineService
from app.features.linux_inspections.router import get_linux_inspection_service
from app.features.linux_inspections.schemas import LinuxInspectionRequest
from app.features.linux_inspections.service import LinuxInspectionService
from app.features.switch_inspections.router import get_switch_inspection_service
from app.features.switch_inspections.schemas import SwitchInspectionRequest
from app.features.switch_inspections.service import SwitchInspectionService

router = APIRouter(prefix="/baseline-checks")


def get_baseline_service(
    session: AsyncSession = Depends(get_db_session),
    linux_service: LinuxInspectionService = Depends(get_linux_inspection_service),
    switch_service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> BaselineService:
    return BaselineService(
        session,
        BaselineCheckResultRepository(session),
        linux_service,
        switch_service,
    )


@router.get(
    "",
    response_model=list[BaselineRunRead],
    summary="List baseline runs",
    description="Return baseline views grouped by inspection so baseline results can be reviewed independently.",
)
async def list_baseline_runs(
    device_type: str | None = Query(default=None, pattern="^(linux|switch)$"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(pass|fail|unknown|not_applicable)$"),
    service: BaselineService = Depends(get_baseline_service),
) -> list[BaselineRunRead]:
    return await service.list_runs(device_type=device_type, status=status_filter)


@router.post(
    "/linux/run",
    response_model=BaselineRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run Linux baseline check",
    description="Run Linux inspection plus baseline evaluation through the baseline feature entrypoint.",
)
@limiter.limit(get_settings().linux_inspection_rate_limit)
async def run_linux_baseline(
    request: Request,
    payload: LinuxInspectionRequest,
    service: BaselineService = Depends(get_baseline_service),
) -> BaselineRunRead:
    return await service.run_linux(payload)


@router.post(
    "/switch/run",
    response_model=BaselineRunRead,
    status_code=status.HTTP_200_OK,
    summary="Run switch baseline check",
    description="Run switch inspection plus baseline evaluation through the baseline feature entrypoint.",
)
@limiter.limit(get_settings().switch_inspection_rate_limit)
async def run_switch_baseline(
    request: Request,
    payload: SwitchInspectionRequest,
    service: BaselineService = Depends(get_baseline_service),
) -> BaselineRunRead:
    return await service.run_switch(payload)


@router.post(
    "/linux/{inspection_id}/rerun",
    response_model=BaselineRunRead,
    status_code=status.HTTP_200_OK,
    summary="Re-run Linux baseline checks",
    description="Re-evaluate baseline rules against a saved Linux inspection without reconnecting to the host.",
)
async def rerun_linux_baseline(
    inspection_id: int,
    service: BaselineService = Depends(get_baseline_service),
) -> BaselineRunRead:
    return await service.rerun_linux(inspection_id)


@router.post(
    "/switch/{inspection_id}/rerun",
    response_model=BaselineRunRead,
    status_code=status.HTTP_200_OK,
    summary="Re-run switch baseline checks",
    description="Re-evaluate baseline rules against a saved switch inspection without reconnecting to the device.",
)
async def rerun_switch_baseline(
    inspection_id: int,
    service: BaselineService = Depends(get_baseline_service),
) -> BaselineRunRead:
    return await service.rerun_switch(inspection_id)
