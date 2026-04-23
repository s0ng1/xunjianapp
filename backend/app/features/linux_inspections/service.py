from __future__ import annotations

import logging
from functools import partial

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.assets.repository import AssetRepository
from app.features.baseline.linux_rule_collector import LEGACY_LINUX_COLLECTION_PLAN, merge_collection_plans
from app.features.baseline.linux_rule_engine import LinuxBaselineRuleEngine
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.baseline.schemas import BaselineCheckRead
from app.features.linux_inspections.client import LinuxInspectionExecution, LinuxInspectorClient
from app.features.linux_inspections.repository import LinuxInspectionRepository
from app.features.linux_inspections.schemas import LinuxInspectionRead, LinuxInspectionRequest

logger = logging.getLogger(__name__)


class LinuxInspectionService:
    def __init__(
        self,
        session: AsyncSession,
        inspector: LinuxInspectorClient,
        rule_engine: LinuxBaselineRuleEngine,
    ) -> None:
        self.session = session
        self.repository = LinuxInspectionRepository(session)
        self.asset_repository = AssetRepository(session)
        self.baseline_repository = BaselineCheckResultRepository(session)
        self.inspector = inspector
        self.rule_engine = rule_engine

    async def run_inspection(self, payload: LinuxInspectionRequest) -> LinuxInspectionRead:
        return await self.run_inspection_with_credentials(
            ip=str(payload.ip),
            username=payload.username,
            password=payload.password.get_secret_value(),
        )

    async def run_inspection_with_credentials(
        self,
        *,
        ip: str,
        username: str,
        password: str,
        asset_id: int | None = None,
        port: int = 22,
    ) -> LinuxInspectionRead:
        collection_plan = merge_collection_plans(tuple(LEGACY_LINUX_COLLECTION_PLAN), self.rule_engine.build_collection_plan())
        execution = await to_thread.run_sync(
            partial(
                self.inspector.inspect,
                ip=ip,
                username=username,
                password=password,
                port=port,
                collection_plan=collection_plan,
            )
        )
        self._log_result(ip=ip, username=username, execution=execution)
        try:
            resolved_asset_id = asset_id if asset_id is not None else await self._resolve_asset_id(ip)
            inspection = await self.repository.add(
                asset_id=resolved_asset_id,
                ip=ip,
                username=username,
                success=execution.success,
                message=execution.message,
                open_ports=execution.open_ports.model_dump() if execution.open_ports is not None else None,
                ssh_config=execution.ssh_config.model_dump() if execution.ssh_config is not None else None,
                firewall_status=execution.firewall_status.model_dump() if execution.firewall_status is not None else None,
                time_sync_status=execution.time_sync_status.model_dump() if execution.time_sync_status is not None else None,
                auditd_status=execution.auditd_status.model_dump() if execution.auditd_status is not None else None,
                collected_data=execution.collected_data,
            )
            baseline_results = await self.baseline_repository.add_for_linux_inspection(
                linux_inspection_id=inspection.id,
                results=self.rule_engine.evaluate_linux_inspection(self._build_snapshot(execution)),
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return self._to_read_model(inspection, baseline_results)

    async def list_inspections(self, *, skip: int = 0, limit: int = 100) -> list[LinuxInspectionRead]:
        inspections = await self.repository.list_all(skip=skip, limit=limit)
        inspection_ids = [inspection.id for inspection in inspections]
        results_map = await self.baseline_repository.list_by_linux_inspection_ids(inspection_ids)
        return [self._to_read_model(inspection, results_map.get(inspection.id, [])) for inspection in inspections]

    def _to_read_model(self, inspection, baseline_results: list[BaselineCheckRead]) -> LinuxInspectionRead:
        return LinuxInspectionRead(
            id=inspection.id,
            asset_id=inspection.asset_id,
            ip=inspection.ip,
            username=inspection.username,
            success=inspection.success,
            message=inspection.message,
            open_ports=inspection.open_ports,
            ssh_config=inspection.ssh_config,
            firewall_status=inspection.firewall_status,
            time_sync_status=inspection.time_sync_status,
            auditd_status=inspection.auditd_status,
            collected_data=inspection.collected_data or {},
            baseline_results=baseline_results,
            created_at=inspection.created_at,
        )

    def _log_result(self, *, ip: str, username: str, execution: LinuxInspectionExecution) -> None:
        level = logging.INFO if execution.success else logging.WARNING
        logger.log(
            level,
            "Linux inspection finished ip=%s username=%s success=%s message=%s",
            ip,
            username,
            execution.success,
            execution.message,
        )

    async def _resolve_asset_id(self, ip: str) -> int | None:
        asset = await self.asset_repository.get_by_ip(ip)
        return asset.id if asset is not None else None

    def _build_snapshot(self, execution: LinuxInspectionExecution) -> dict:
        return {
            "success": execution.success,
            "message": execution.message,
            "open_ports": execution.open_ports.model_dump() if execution.open_ports is not None else None,
            "ssh_config": execution.ssh_config.model_dump() if execution.ssh_config is not None else None,
            "firewall_status": execution.firewall_status.model_dump() if execution.firewall_status is not None else None,
            "time_sync_status": execution.time_sync_status.model_dump() if execution.time_sync_status is not None else None,
            "auditd_status": execution.auditd_status.model_dump() if execution.auditd_status is not None else None,
            "collected_data": execution.collected_data or {},
        }
