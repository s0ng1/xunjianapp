from __future__ import annotations

from functools import partial

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.features.assets.repository import AssetCredentialRepository, AssetRepository
from app.features.assets.schemas import AssetCreate, AssetRead, AssetUpdate, build_asset_read
from app.features.assets.secret_store import CredentialCipher
from app.features.baseline.schemas import BaselineRunRead
from app.features.linux_inspections.service import LinuxInspectionService
from app.features.port_scans.schemas import PortScanRead
from app.features.port_scans.service import PortScanService
from app.features.ssh_test.client import SSHConnector
from app.features.ssh_test.schemas import SSHTestResponse
from app.features.switch_inspections.service import SwitchInspectionService


class AssetService:
    def __init__(self, session: AsyncSession, cipher: CredentialCipher) -> None:
        self.session = session
        self.repository = AssetRepository(session)
        self.credential_repository = AssetCredentialRepository(session)
        self.cipher = cipher

    async def create_asset(self, payload: AssetCreate) -> AssetRead:
        async with self.session.begin():
            existing_asset = await self.repository.get_by_ip(str(payload.ip))
            if existing_asset is not None:
                raise ConflictError(f"Asset with IP {payload.ip} already exists")

            credential_id: int | None = None
            if payload.credential_password is not None:
                credential = await self.credential_repository.add(
                    encrypted_password=self.cipher.encrypt(payload.credential_password.get_secret_value())
                )
                credential_id = credential.id

            asset = await self.repository.add(
                ip=str(payload.ip),
                asset_type=payload.type,
                name=payload.name,
                connection_type=payload.connection_type,
                port=payload.port,
                username=payload.username,
                vendor=payload.vendor if payload.type == "switch" else None,
                credential_id=credential_id,
                is_enabled=payload.is_enabled,
            )
        return build_asset_read(
            asset_id=asset.id,
            ip=asset.ip,
            asset_type=asset.asset_type,
            name=asset.name,
            connection_type=asset.connection_type,
            port=asset.port,
            username=asset.username,
            vendor=asset.vendor,
            credential_id=asset.credential_id,
            is_enabled=asset.is_enabled,
            created_at=asset.created_at,
        )

    async def list_assets(self, *, skip: int = 0, limit: int = 100) -> list[AssetRead]:
        assets = await self.repository.list_all(skip=skip, limit=limit)
        return [
            build_asset_read(
                asset_id=asset.id,
                ip=asset.ip,
                asset_type=asset.asset_type,
                name=asset.name,
                connection_type=asset.connection_type,
                port=asset.port,
                username=asset.username,
                vendor=asset.vendor,
                credential_id=asset.credential_id,
                is_enabled=asset.is_enabled,
                created_at=asset.created_at,
            )
            for asset in assets
        ]

    async def update_asset(self, asset_id: int, payload: AssetUpdate) -> AssetRead:
        async with self.session.begin():
            asset = await self.repository.get_by_id(asset_id)
            if asset is None:
                raise NotFoundError("Asset", asset_id)

            if "name" in payload.model_fields_set and payload.name is not None:
                asset.name = payload.name
            if "connection_type" in payload.model_fields_set and payload.connection_type is not None:
                asset.connection_type = payload.connection_type
            if "port" in payload.model_fields_set and payload.port is not None:
                asset.port = payload.port
            if "username" in payload.model_fields_set:
                asset.username = payload.username
            if "is_enabled" in payload.model_fields_set and payload.is_enabled is not None:
                asset.is_enabled = payload.is_enabled
            if asset.asset_type == "switch" and "vendor" in payload.model_fields_set:
                asset.vendor = payload.vendor

            if "credential_password" in payload.model_fields_set and payload.credential_password is not None:
                encrypted_password = self.cipher.encrypt(payload.credential_password.get_secret_value())
                if asset.credential_id is None:
                    credential = await self.credential_repository.add(encrypted_password=encrypted_password)
                    asset.credential_id = credential.id
                else:
                    credential = await self.credential_repository.get_by_id(asset.credential_id)
                    if credential is None:
                        credential = await self.credential_repository.add(encrypted_password=encrypted_password)
                        asset.credential_id = credential.id
                    else:
                        credential.encrypted_password = encrypted_password
                        await self.credential_repository.save(credential)

            self._validate_execution_config(asset)
            await self.repository.save(asset)

        return build_asset_read(
            asset_id=asset.id,
            ip=asset.ip,
            asset_type=asset.asset_type,
            name=asset.name,
            connection_type=asset.connection_type,
            port=asset.port,
            username=asset.username,
            vendor=asset.vendor,
            credential_id=asset.credential_id,
            is_enabled=asset.is_enabled,
            created_at=asset.created_at,
        )

    async def delete_asset(self, asset_id: int) -> None:
        async with self.session.begin():
            asset = await self.repository.get_by_id(asset_id)
            if asset is None:
                raise NotFoundError("Asset", asset_id)

            credential_id = asset.credential_id
            await self.repository.delete(asset)
            if credential_id is not None:
                remaining_references = await self.repository.count_by_credential_id(
                    credential_id,
                    exclude_asset_id=asset.id,
                )
                if remaining_references == 0:
                    credential = await self.credential_repository.get_by_id(credential_id)
                    if credential is not None:
                        await self.credential_repository.delete(credential)

    def _validate_execution_config(self, asset) -> None:
        has_stored_credential = asset.credential_id is not None

        if asset.connection_type == "ssh" and has_stored_credential and not asset.username:
            raise AppError(
                message="username is required when a stored credential is configured",
                status_code=422,
                code="asset_missing_username",
            )

        if asset.asset_type == "switch" and has_stored_credential and not asset.vendor:
            raise AppError(
                message="vendor is required for switch assets with stored credentials",
                status_code=422,
                code="asset_missing_vendor",
            )


class AssetExecutionService:
    def __init__(
        self,
        session: AsyncSession,
        cipher: CredentialCipher,
        ssh_connector: SSHConnector,
        port_scan_service: PortScanService,
        linux_service: LinuxInspectionService,
        switch_service: SwitchInspectionService,
    ) -> None:
        self.session = session
        self.repository = AssetRepository(session)
        self.credential_repository = AssetCredentialRepository(session)
        self.cipher = cipher
        self.ssh_connector = ssh_connector
        self.port_scan_service = port_scan_service
        self.linux_service = linux_service
        self.switch_service = switch_service

    async def test_ssh(self, asset_id: int) -> SSHTestResponse:
        asset = await self._get_enabled_asset(asset_id)
        self._ensure_ssh_ready(asset)
        password = await self._resolve_password(asset.credential_id)
        result = await to_thread.run_sync(
            partial(
                self.ssh_connector.test_connection,
                ip=asset.ip,
                username=asset.username or "",
                password=password,
                port=asset.port,
            )
        )
        return SSHTestResponse(success=result.success, message=result.message)

    async def run_port_scan(self, asset_id: int, *, ports: list[int] | None = None) -> PortScanRead:
        asset = await self._get_enabled_asset(asset_id)
        return await self.port_scan_service.run_scan_for_target(
            ip=asset.ip,
            ports=ports or None,
            asset_id=asset.id,
        )

    async def run_inspection(self, asset_id: int) -> BaselineRunRead:
        asset = await self._get_enabled_asset(asset_id)
        self._ensure_ssh_ready(asset)
        password = await self._resolve_password(asset.credential_id)

        if asset.asset_type == "linux":
            inspection = await self.linux_service.run_inspection_with_credentials(
                ip=asset.ip,
                username=asset.username or "",
                password=password,
                asset_id=asset.id,
                port=asset.port,
            )
            return BaselineRunRead(
                asset_id=inspection.asset_id,
                inspection_id=inspection.id,
                source_type="linux_inspection",
                device_type="linux",
                ip=inspection.ip,
                username=inspection.username,
                success=inspection.success,
                message=inspection.message,
                baseline_results=inspection.baseline_results,
                created_at=inspection.created_at,
            )

        if asset.asset_type == "switch":
            inspection = await self.switch_service.inspect_with_credentials(
                ip=asset.ip,
                username=asset.username or "",
                password=password,
                vendor=asset.vendor or "",
                asset_id=asset.id,
                port=asset.port,
            )
            return BaselineRunRead(
                asset_id=inspection.asset_id,
                inspection_id=inspection.id,
                source_type="switch_inspection",
                device_type="switch",
                ip=inspection.ip,
                username=inspection.username,
                vendor=inspection.vendor,
                success=inspection.success,
                message=inspection.message,
                baseline_results=inspection.baseline_results,
                created_at=inspection.created_at,
            )

        raise AppError(
            message=f"Unsupported asset type for inspection: {asset.asset_type}",
            status_code=422,
            code="unsupported_asset_type",
        )

    async def run_baseline(self, asset_id: int) -> BaselineRunRead:
        return await self.run_inspection(asset_id)

    async def _get_enabled_asset(self, asset_id: int):
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise NotFoundError("Asset", asset_id)
        if not asset.is_enabled:
            raise AppError(message="Asset is disabled", status_code=409, code="asset_disabled")
        return asset

    def _ensure_ssh_ready(self, asset) -> None:
        if asset.connection_type != "ssh":
            raise AppError(
                message=f"Unsupported connection type: {asset.connection_type}",
                status_code=422,
                code="unsupported_connection_type",
            )
        if not asset.username:
            raise AppError(
                message="Asset username is not configured",
                status_code=422,
                code="asset_missing_username",
            )
        if asset.credential_id is None:
            raise AppError(
                message="Asset credential is not configured",
                status_code=422,
                code="asset_missing_credential",
            )
        if asset.asset_type == "switch" and not asset.vendor:
            raise AppError(
                message="Switch asset vendor is not configured",
                status_code=422,
                code="asset_missing_vendor",
            )

    async def _resolve_password(self, credential_id: int | None) -> str:
        if credential_id is None:
            raise AppError(
                message="Asset credential is not configured",
                status_code=422,
                code="asset_missing_credential",
            )

        credential = await self.credential_repository.get_by_id(credential_id)
        if credential is None:
            raise AppError(
                message=f"Credential not found: {credential_id}",
                status_code=404,
                code="credential_not_found",
            )
        return self.cipher.decrypt(credential.encrypted_password)
