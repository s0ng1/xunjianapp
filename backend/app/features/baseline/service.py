from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.baseline.schemas import BaselineCheckRead, BaselineRunRead
from app.features.linux_inspections.schemas import LinuxInspectionRead, LinuxInspectionRequest
from app.features.linux_inspections.service import LinuxInspectionService
from app.features.switch_inspections.schemas import SwitchInspectionRequest, SwitchInspectionResponse
from app.features.switch_inspections.service import SwitchInspectionService


class BaselineService:
    def __init__(
        self,
        session: AsyncSession,
        repository: BaselineCheckResultRepository,
        linux_service: LinuxInspectionService,
        switch_service: SwitchInspectionService,
    ) -> None:
        self.session = session
        self.repository = repository
        self.linux_service = linux_service
        self.switch_service = switch_service

    async def run_linux(self, payload: LinuxInspectionRequest) -> BaselineRunRead:
        inspection = await self.linux_service.run_inspection(payload)
        return self._from_linux_read(inspection)

    async def run_switch(self, payload: SwitchInspectionRequest) -> BaselineRunRead:
        inspection = await self.switch_service.inspect(payload)
        return self._from_switch_read(inspection)

    async def list_runs(
        self,
        *,
        device_type: str | None = None,
        status: str | None = None,
    ) -> list[BaselineRunRead]:
        runs: list[BaselineRunRead] = []

        if device_type in (None, "linux"):
            inspections = await self.linux_service.repository.list_all()
            results_map = await self.repository.list_by_linux_inspection_ids([inspection.id for inspection in inspections])
            runs.extend(
                self._from_linux_model(inspection, results_map.get(inspection.id, [])) for inspection in inspections
            )

        if device_type in (None, "switch"):
            inspections = await self.switch_service.repository.list_all()
            results_map = await self.repository.list_by_switch_inspection_ids([inspection.id for inspection in inspections])
            runs.extend(
                self._from_switch_model(inspection, results_map.get(inspection.id, [])) for inspection in inspections
            )

        if status is not None:
            normalized_status = status.strip().lower()
            runs = [run for run in runs if self._has_status(run.baseline_results, normalized_status)]

        return sorted(runs, key=lambda item: item.created_at, reverse=True)

    async def rerun_linux(self, inspection_id: int) -> BaselineRunRead:
        async with self.session.begin():
            inspection = await self.linux_service.repository.get_by_id(inspection_id)
            if inspection is None:
                raise AppError(message="Linux inspection not found", status_code=404, code="linux_inspection_not_found")

            baseline_results = await self.repository.replace_for_linux_inspection(
                linux_inspection_id=inspection.id,
                results=self.linux_service.rule_engine.evaluate_linux_inspection(self._build_linux_snapshot(inspection)),
            )

        return self._from_linux_model(inspection, baseline_results)

    async def rerun_switch(self, inspection_id: int) -> BaselineRunRead:
        async with self.session.begin():
            inspection = await self.switch_service.repository.get_by_id(inspection_id)
            if inspection is None:
                raise AppError(
                    message="Switch inspection not found",
                    status_code=404,
                    code="switch_inspection_not_found",
                )

            baseline_results = await self.repository.replace_for_switch_inspection(
                switch_inspection_id=inspection.id,
                results=self.switch_service.rule_engine.evaluate_switch_inspection(
                    self._build_switch_snapshot(inspection)
                ),
            )

        return self._from_switch_model(inspection, baseline_results)

    def _from_linux_read(self, inspection: LinuxInspectionRead) -> BaselineRunRead:
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

    def _from_switch_read(self, inspection: SwitchInspectionResponse) -> BaselineRunRead:
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

    def _from_linux_model(self, inspection, baseline_results: list[BaselineCheckRead]) -> BaselineRunRead:
        return BaselineRunRead(
            asset_id=inspection.asset_id,
            inspection_id=inspection.id,
            source_type="linux_inspection",
            device_type="linux",
            ip=inspection.ip,
            username=inspection.username,
            success=inspection.success,
            message=inspection.message,
            baseline_results=baseline_results,
            created_at=inspection.created_at,
        )

    def _from_switch_model(self, inspection, baseline_results: list[BaselineCheckRead]) -> BaselineRunRead:
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
            baseline_results=baseline_results,
            created_at=inspection.created_at,
        )

    def _has_status(self, baseline_results: Iterable[BaselineCheckRead], status: str) -> bool:
        return any(item.status == status for item in baseline_results)

    def _build_linux_snapshot(self, inspection) -> dict:
        return {
            "success": inspection.success,
            "message": inspection.message,
            "open_ports": inspection.open_ports,
            "ssh_config": inspection.ssh_config,
            "firewall_status": inspection.firewall_status,
            "time_sync_status": inspection.time_sync_status,
            "auditd_status": inspection.auditd_status,
            "collected_data": inspection.collected_data or {},
        }

    def _build_switch_snapshot(self, inspection) -> dict:
        return {
            "success": inspection.success,
            "message": inspection.message,
            "vendor": inspection.vendor,
            "raw_config": inspection.raw_config,
        }
