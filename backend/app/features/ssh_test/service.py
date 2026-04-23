from __future__ import annotations

import logging
from functools import partial

from anyio import to_thread

from app.features.ssh_test.client import SSHConnectionResult, SSHConnector
from app.features.ssh_test.schemas import SSHTestRequest, SSHTestResponse

logger = logging.getLogger(__name__)


class SSHTestService:
    def __init__(self, connector: SSHConnector) -> None:
        self.connector = connector

    async def test_connection(self, payload: SSHTestRequest) -> SSHTestResponse:
        result = await to_thread.run_sync(
            partial(
                self.connector.test_connection,
                ip=str(payload.ip),
                username=payload.username,
                password=payload.password.get_secret_value(),
            )
        )
        self._log_result(ip=str(payload.ip), username=payload.username, result=result)
        return SSHTestResponse(success=result.success, message=result.message)

    def _log_result(self, *, ip: str, username: str, result: SSHConnectionResult) -> None:
        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level,
            "SSH test finished ip=%s username=%s success=%s message=%s",
            ip,
            username,
            result.success,
            result.message,
        )
