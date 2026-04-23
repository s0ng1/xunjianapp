from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.features.baseline.engine import BaselineRuleEngine
from app.features.switch_inspections.client import H3CSwitchInspectorClient
from app.features.switch_inspections.schemas import (
    H3CInspectionRequest,
    H3CInspectionResponse,
    SwitchInspectionRequest,
    SwitchInspectionResponse,
)
from app.features.switch_inspections.service import SwitchInspectionService

router = APIRouter(prefix="/switch-inspections")


def get_h3c_switch_inspector(settings: Settings = Depends(get_settings)) -> H3CSwitchInspectorClient:
    return H3CSwitchInspectorClient(
        connection_timeout_seconds=settings.ssh_connection_timeout_seconds,
        command_read_timeout_seconds=settings.ssh_command_read_timeout_seconds,
    )


def get_switch_baseline_rule_engine() -> BaselineRuleEngine:
    return BaselineRuleEngine()


def get_switch_inspectors(
    h3c_inspector: H3CSwitchInspectorClient = Depends(get_h3c_switch_inspector),
) -> dict[str, H3CSwitchInspectorClient]:
    return {"h3c": h3c_inspector}


def get_switch_inspection_service(
    session: AsyncSession = Depends(get_db_session),
    inspectors: dict[str, H3CSwitchInspectorClient] = Depends(get_switch_inspectors),
    rule_engine: BaselineRuleEngine = Depends(get_switch_baseline_rule_engine),
) -> SwitchInspectionService:
    return SwitchInspectionService(
        session,
        inspectors,
        rule_engine,
    )


@router.post(
    "/run",
    response_model=SwitchInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run switch inspection",
    description="Connect to a supported switch over SSH, save the result, and return the inspection output.",
)
@limiter.limit(get_settings().switch_inspection_rate_limit)
async def run_switch_inspection(
    request: Request,
    payload: SwitchInspectionRequest,
    service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> SwitchInspectionResponse:
    return await service.inspect(payload)


@router.get(
    "",
    response_model=list[SwitchInspectionResponse],
    summary="List switch inspections",
    description="List saved switch inspection results ordered by newest first.",
)
async def list_switch_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> list[SwitchInspectionResponse]:
    return await service.list_inspections(skip=skip, limit=limit)


@router.post(
    "/h3c/run",
    response_model=H3CInspectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run H3C switch inspection",
    description="Compatibility route for H3C switch inspection. Prefer `/switch-inspections/run` with `vendor=h3c`.",
)
@limiter.limit(get_settings().switch_inspection_rate_limit)
async def run_h3c_switch_inspection(
    request: Request,
    payload: H3CInspectionRequest,
    service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> H3CInspectionResponse:
    return await service.inspect_h3c(payload)


@router.get(
    "/h3c",
    response_model=list[H3CInspectionResponse],
    summary="List H3C switch inspections",
    description="Compatibility route for listing H3C switch inspections. Prefer `/switch-inspections`.",
)
async def list_h3c_switch_inspections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> list[H3CInspectionResponse]:
    return await service.list_inspections(vendor="h3c", skip=skip, limit=limit)
