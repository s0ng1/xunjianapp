from fastapi import APIRouter, Depends, Request, status

from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.features.ssh_test.client import SSHConnector
from app.features.ssh_test.schemas import SSHTestRequest, SSHTestResponse
from app.features.ssh_test.service import SSHTestService

router = APIRouter(prefix="/ssh")


def get_ssh_connector(settings: Settings = Depends(get_settings)) -> SSHConnector:
    return SSHConnector(timeout_seconds=settings.ssh_connection_timeout_seconds)


def get_ssh_test_service(connector: SSHConnector = Depends(get_ssh_connector)) -> SSHTestService:
    return SSHTestService(connector)


@router.post(
    "/test",
    response_model=SSHTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test SSH connection",
    description="Test SSH login with an IP address, username, and password without persisting credentials.",
)
@limiter.limit(get_settings().ssh_test_rate_limit)
async def test_ssh_connection(
    request: Request,
    payload: SSHTestRequest,
    service: SSHTestService = Depends(get_ssh_test_service),
) -> SSHTestResponse:
    return await service.test_connection(payload)
