from __future__ import annotations

import logging
from collections.abc import Mapping
from functools import partial

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.features.assets.repository import AssetRepository
from app.features.baseline.engine import BaselineRuleEngine
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.baseline.schemas import BaselineCheckRead
from app.features.switch_inspections.client import H3CSwitchInspectorClient, SwitchInspectionResult
from app.features.switch_inspections.repository import SwitchInspectionRepository
from app.features.switch_inspections.schemas import (
    H3CInspectionRequest,
    SwitchInspectionRequest,
    SwitchInspectionResponse,
)

logger = logging.getLogger(__name__)


class SwitchInspectionService:
    def __init__(
        self,
        session: AsyncSession,
        inspectors: Mapping[str, H3CSwitchInspectorClient],
        rule_engine: BaselineRuleEngine,
    ) -> None:
        self.session = session
        self.repository = SwitchInspectionRepository(session)
        self.asset_repository = AssetRepository(session)
        self.baseline_repository = BaselineCheckResultRepository(session)
        self.inspectors = dict(inspectors)
        self.rule_engine = rule_engine

    async def inspect(self, payload: SwitchInspectionRequest) -> SwitchInspectionResponse:
        return await self.inspect_with_credentials(
            ip=str(payload.ip),
            username=payload.username,
            password=payload.password.get_secret_value(),
            vendor=payload.vendor,
        )

    async def inspect_with_credentials(
        self,
        *,
        ip: str,
        username: str,
        password: str,
        vendor: str,
        asset_id: int | None = None,
        port: int = 22,
    ) -> SwitchInspectionResponse:
        normalized_vendor = self._normalize_vendor(vendor)
        display_vendor = self._display_vendor(normalized_vendor)
        inspector = self._get_inspector(normalized_vendor)
        result = await to_thread.run_sync(
            partial(
                inspector.inspect,
                ip=ip,
                username=username,
                password=password,
                port=port,
            )
        )
        self._log_result(ip=ip, username=username, vendor=display_vendor, result=result)
        try:
            resolved_asset_id = asset_id if asset_id is not None else await self._resolve_asset_id(ip)
            inspection = await self.repository.add(
                asset_id=resolved_asset_id,
                ip=ip,
                username=username,
                vendor=display_vendor,
                success=result.success,
                message=result.message,
                raw_config=result.raw_config,
            )
            baseline_results = await self.baseline_repository.add_for_switch_inspection(
                switch_inspection_id=inspection.id,
                results=self.rule_engine.evaluate_switch_inspection(
                    inspection={
                        "success": result.success,
                        "message": result.message,
                        "vendor": display_vendor,
                        "raw_config": result.raw_config,
                    }
                ),
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return self._to_read_model(inspection, baseline_results)

    async def inspect_h3c(self, payload: H3CInspectionRequest) -> SwitchInspectionResponse:
        return await self.inspect(
            SwitchInspectionRequest(
                ip=payload.ip,
                username=payload.username,
                password=payload.password,
                vendor="h3c",
            )
        )

    async def list_inspections(
        self,
        *,
        vendor: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SwitchInspectionResponse]:
        normalized_vendor = self._normalize_vendor(vendor) if vendor is not None else None
        display_vendor = self._display_vendor(normalized_vendor) if normalized_vendor is not None else None
        inspections = await self.repository.list_all(vendor=display_vendor, skip=skip, limit=limit)
        inspection_ids = [inspection.id for inspection in inspections]
        results_map = await self.baseline_repository.list_by_switch_inspection_ids(inspection_ids)
        return [self._to_read_model(inspection, results_map.get(inspection.id, [])) for inspection in inspections]

    def _to_read_model(
        self,
        inspection,
        baseline_results: list[BaselineCheckRead],
    ) -> SwitchInspectionResponse:
        return SwitchInspectionResponse(
            id=inspection.id,
            asset_id=inspection.asset_id,
            ip=inspection.ip,
            username=inspection.username,
            success=inspection.success,
            vendor=inspection.vendor,
            message=inspection.message,
            raw_config=inspection.raw_config,
            baseline_results=baseline_results,
            created_at=inspection.created_at,
        )

    def _get_inspector(self, vendor: str) -> H3CSwitchInspectorClient:
        inspector = self.inspectors.get(vendor)
        if inspector is None:
            raise AppError(message=f"Unsupported switch vendor: {vendor}", status_code=422, code="unsupported_vendor")
        return inspector

    async def _resolve_asset_id(self, ip: str) -> int | None:
        asset = await self.asset_repository.get_by_ip(ip)
        return asset.id if asset is not None else None

    def _normalize_vendor(self, vendor: str) -> str:
        return vendor.strip().lower()

    def _display_vendor(self, vendor: str) -> str:
        return vendor.upper()

    def _log_result(self, *, ip: str, username: str, vendor: str, result: SwitchInspectionResult) -> None:
        level = logging.INFO if result.success else logging.WARNING
        logger.log(
            level,
            "Switch inspection finished vendor=%s ip=%s username=%s success=%s message=%s",
            vendor,
            ip,
            username,
            result.success,
            result.message,
        )
