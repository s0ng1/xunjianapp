from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.features.assets.schemas import AssetCreate, AssetPortScanRequest, AssetRead, AssetUpdate
from app.features.assets.secret_store import CredentialCipher
from app.features.assets.service import AssetExecutionService, AssetService
from app.features.baseline.schemas import BaselineRunRead
from app.features.linux_inspections.router import get_linux_inspection_service
from app.features.linux_inspections.service import LinuxInspectionService
from app.features.port_scans.router import get_port_scan_service
from app.features.port_scans.schemas import PortScanRead
from app.features.port_scans.service import PortScanService
from app.features.ssh_test.router import get_ssh_connector
from app.features.ssh_test.client import SSHConnector
from app.features.ssh_test.schemas import SSHTestResponse
from app.features.switch_inspections.router import get_switch_inspection_service
from app.features.switch_inspections.service import SwitchInspectionService

router = APIRouter(prefix="/assets")


def get_asset_cipher(settings: Settings = Depends(get_settings)) -> CredentialCipher:
    return CredentialCipher(encryption_key=settings.credential_encryption_key)


def get_asset_service(
    session: AsyncSession = Depends(get_db_session),
    cipher: CredentialCipher = Depends(get_asset_cipher),
) -> AssetService:
    return AssetService(session, cipher)


def get_asset_execution_service(
    session: AsyncSession = Depends(get_db_session),
    cipher: CredentialCipher = Depends(get_asset_cipher),
    ssh_connector: SSHConnector = Depends(get_ssh_connector),
    port_scan_service: PortScanService = Depends(get_port_scan_service),
    linux_service: LinuxInspectionService = Depends(get_linux_inspection_service),
    switch_service: SwitchInspectionService = Depends(get_switch_inspection_service),
) -> AssetExecutionService:
    return AssetExecutionService(
        session,
        cipher,
        ssh_connector,
        port_scan_service,
        linux_service,
        switch_service,
    )


@router.post(
    "",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create asset",
    description="Create a new managed asset with executable connection metadata.",
)
async def create_asset(
    payload: AssetCreate,
    service: AssetService = Depends(get_asset_service),
) -> AssetRead:
    return await service.create_asset(payload)


@router.get(
    "",
    response_model=list[AssetRead],
    summary="List assets",
    description="Return all managed assets ordered by newest first.",
)
async def list_assets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: AssetService = Depends(get_asset_service),
) -> list[AssetRead]:
    return await service.list_assets(skip=skip, limit=limit)


@router.patch(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Update asset",
    description="Update the stored connection profile for an existing managed asset.",
)
async def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    service: AssetService = Depends(get_asset_service),
) -> AssetRead:
    return await service.update_asset(asset_id, payload)


@router.post(
    "/{asset_id}/ssh-test",
    response_model=SSHTestResponse,
    summary="Test SSH connection for asset",
    description="Use the stored asset connection profile and credential reference to test SSH.",
)
async def test_asset_ssh(
    asset_id: int,
    service: AssetExecutionService = Depends(get_asset_execution_service),
) -> SSHTestResponse:
    return await service.test_ssh(asset_id)


@router.post(
    "/{asset_id}/port-scan",
    response_model=PortScanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run port scan for asset",
    description="Run a port scan using the stored asset IP and save the result with the asset reference.",
)
async def run_asset_port_scan(
    asset_id: int,
    payload: AssetPortScanRequest,
    service: AssetExecutionService = Depends(get_asset_execution_service),
) -> PortScanRead:
    return await service.run_port_scan(asset_id, ports=payload.ports or None)


@router.post(
    "/{asset_id}/inspect",
    response_model=BaselineRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run inspection for asset",
    description="Run the asset-linked inspection flow and return the saved baseline summary.",
)
async def run_asset_inspection(
    asset_id: int,
    service: AssetExecutionService = Depends(get_asset_execution_service),
) -> BaselineRunRead:
    return await service.run_inspection(asset_id)


@router.post(
    "/{asset_id}/baseline",
    response_model=BaselineRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="Run baseline for asset",
    description="Run the asset-linked baseline entrypoint using the stored execution profile.",
)
async def run_asset_baseline(
    asset_id: int,
    service: AssetExecutionService = Depends(get_asset_execution_service),
) -> BaselineRunRead:
    return await service.run_baseline(asset_id)


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete asset",
    description="Delete an asset by its numeric identifier.",
)
async def delete_asset(
    asset_id: int,
    service: AssetService = Depends(get_asset_service),
) -> Response:
    await service.delete_asset(asset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
