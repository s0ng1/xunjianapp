import logging
from dataclasses import dataclass

from app.features.scheduled_tasks.models import ScheduledTask

logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionResult:
    success: bool
    message: str


class ScheduledTaskExecutor:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    async def execute(self, task: ScheduledTask) -> TaskExecutionResult:
        async with self.session_factory() as session:
            from app.features.assets.secret_store import CredentialCipher
            from app.features.assets.service import AssetExecutionService
            from app.features.baseline.engine import BaselineRuleEngine
            from app.features.baseline.linux_rule_engine import LinuxBaselineRuleEngine
            from app.features.linux_inspections.client import LinuxInspectorClient
            from app.features.linux_inspections.service import LinuxInspectionService
            from app.features.port_scans.client import PortScanner
            from app.features.port_scans.service import PortScanService
            from app.features.ssh_test.client import SSHConnector
            from app.features.switch_inspections.client import H3CSwitchInspectorClient
            from app.features.switch_inspections.service import SwitchInspectionService

            cipher = CredentialCipher()
            ssh_connector = SSHConnector()
            port_scanner = PortScanner()
            linux_inspector = LinuxInspectorClient(
                connection_timeout_seconds=10,
                command_read_timeout_seconds=120,
            )
            h3c_inspector = H3CSwitchInspectorClient(
                connection_timeout_seconds=10,
                command_read_timeout_seconds=120,
            )
            asset_service = AssetExecutionService(
                session=session,
                cipher=cipher,
                ssh_connector=ssh_connector,
                port_scan_service=PortScanService(session, port_scanner),
                linux_service=LinuxInspectionService(session, linux_inspector, LinuxBaselineRuleEngine()),
                switch_service=SwitchInspectionService(session, {"h3c": h3c_inspector}, BaselineRuleEngine()),
            )
            try:
                task_type = task.task_type
                params = task.params or {}
                if task_type == "ssh_test":
                    if task.asset_id is None:
                        return TaskExecutionResult(False, "asset_id required")
                    result = await asset_service.test_ssh(task.asset_id)
                    return TaskExecutionResult(result.success, result.message)
                if task_type == "port_scan":
                    if task.asset_id is None:
                        return TaskExecutionResult(False, "asset_id required")
                    result = await asset_service.run_port_scan(task.asset_id, ports=params.get("ports"))
                    return TaskExecutionResult(result.success, result.message)
                if task_type in ("linux_inspection", "switch_inspection", "baseline_check"):
                    if task.asset_id is None:
                        return TaskExecutionResult(False, "asset_id required")
                    result = await asset_service.run_inspection(task.asset_id)
                    return TaskExecutionResult(result.success, result.message)
                return TaskExecutionResult(False, f"Unknown task_type: {task_type}")
            except Exception as exc:
                logger.exception("Scheduled task %s failed", task.id)
                return TaskExecutionResult(False, str(exc))
