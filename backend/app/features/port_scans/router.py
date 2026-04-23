from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.features.port_scans.client import PortScanner
from app.features.port_scans.schemas import PortScanRead, PortScanRequest
from app.features.port_scans.service import PortScanService

router = APIRouter(prefix="/port-scans")


def get_port_scanner(settings: Settings = Depends(get_settings)) -> PortScanner:
    return PortScanner(
        timeout_seconds=settings.port_scan_connect_timeout_seconds,
        default_ports=settings.parsed_port_scan_default_ports,
    )


def get_port_scan_service(
    session: AsyncSession = Depends(get_db_session),
    scanner: PortScanner = Depends(get_port_scanner),
) -> PortScanService:
    return PortScanService(session, scanner)


@router.post(
    "/run",
    response_model=PortScanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run port scan",
    description="Check a target host for open TCP ports and save the scan result.",
)
@limiter.limit(get_settings().port_scan_rate_limit)
async def run_port_scan(
    request: Request,
    payload: PortScanRequest,
    service: PortScanService = Depends(get_port_scan_service),
) -> PortScanRead:
    return await service.run_scan(payload)


@router.get(
    "",
    response_model=list[PortScanRead],
    summary="List port scans",
    description="List saved port scan results ordered by newest first.",
)
async def list_port_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: PortScanService = Depends(get_port_scan_service),
) -> list[PortScanRead]:
    return await service.list_scans(skip=skip, limit=limit)
