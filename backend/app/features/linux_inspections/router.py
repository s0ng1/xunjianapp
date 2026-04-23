from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.features.baseline.linux_rule_engine import LinuxBaselineRuleEngine
from app.features.linux_inspections.client import LinuxInspectorClient
from app.features.linux_inspections.schemas import LinuxInspectionRead, LinuxInspectionRequest
from app.features.linux_inspections.service import LinuxInspectionService

router = APIRouter(prefix="/linux-inspections")


def get_linux_inspector(settings: Settings = Depends(get_settings)) -> LinuxInspectorClient:
    return LinuxInspectorClient(
        connection_timeout_seconds=settings.ssh_connection_timeout_seconds,
        command_read_timeout_seconds=settings.ssh_command_read_timeout_seconds,
    )


def get_linux_baseline_rule_engine() -> LinuxBaselineRuleEngine:
    return LinuxBaselineRuleEngine()


def get_linux_inspection_service(
    session: AsyncSession = Depends(get_db_session),
    inspector: LinuxInspectorClient = Depends(get_linux_inspector),
    rule_engine: LinuxBaselineRuleEngine = Depends(get_linux_baseline_rule_engine),
) -> LinuxInspectionService:
    return LinuxInspectionService(
        session,
        inspector,
        rule_engine,
    )


@router.post(
    "/run",
    response_model=LinuxInspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run Linux inspection",
    description="Run Linux inspection over SSH and save the result.",
)
@limiter.limit(get_settings().linux_inspection_rate_limit)
async def run_linux_inspection(
    request: Request,
    payload: LinuxInspectionRequest,
    service: LinuxInspectionService = Depends(get_linux_inspection_service),
) -> LinuxInspectionRead:
    return await service.run_inspection(payload)


@router.get(
    "",
    response_model=list[LinuxInspectionRead],
    summary="List Linux inspections",
    description="List saved Linux inspection results ordered by newest first.",
)
async def list_linux_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: LinuxInspectionService = Depends(get_linux_inspection_service),
) -> list[LinuxInspectionRead]:
    return await service.list_inspections(skip=skip, limit=limit)
