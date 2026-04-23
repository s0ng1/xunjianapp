import logging

import pytest

from app.core.config import Settings
from app.core.config import get_settings
from app.features.baseline.linux_rule_collector import LinuxCollectCommand
from app.features.baseline.linux_rule_engine import LinuxBaselineRuleEngine
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.linux_inspections import client as linux_client_module
from app.features.linux_inspections.client import LinuxInspectionExecution
from app.features.linux_inspections.router import get_linux_inspector
from app.features.linux_inspections.schemas import (
    AuditdStatusResult,
    FirewallStatusResult,
    OpenPortEntry,
    OpenPortsResult,
    SSHConfigResult,
    TimeSyncStatusResult,
)


class FakeLinuxInspector:
    def __init__(self, execution: LinuxInspectionExecution) -> None:
        self.execution = execution

    def inspect(
        self,
        *,
        ip: str,
        username: str,
        password: str,
        port: int = 22,
        collection_plan=None,
    ) -> LinuxInspectionExecution:
        return self.execution


def _collected_entry(output: str) -> dict[str, str | None]:
    return {
        "type": "command",
        "command": "x",
        "raw_output": output,
        "normalized_output": output,
        "error": None,
    }


def _build_collected_data() -> dict[str, dict]:
    return {
        "shadow_empty_passwords": {"type": "command", "command": "x", "raw_output": "", "error": None},
        "login_defs_pass_max_days": {"type": "config", "command": "x", "raw_output": "90\n", "error": None},
        "telnet_service_state": {"type": "command", "command": "x", "raw_output": "disabled\ninactive\n", "error": None},
        "ssh_service_state": {"type": "command", "command": "x", "raw_output": "enabled\nactive\n", "error": None},
        "legacy_auditd_status": {
            "type": "command",
            "command": "x",
            "raw_output": "__AUDITD__\nactive\n__AUDITCTL__\nenabled 1\n",
            "error": None,
        },
        "uid0_accounts": {"type": "config", "command": "x", "raw_output": "root\n", "error": None},
        "sudoers_risky_entries": {
            "type": "config",
            "command": "x",
            "raw_output": "ops ALL=(ALL) NOPASSWD: ALL\n",
            "error": None,
        },
        "passwd_shadow_permissions": {
            "type": "config",
            "command": "x",
            "raw_output": "/etc/passwd 644 root root\n/etc/shadow 640 root shadow\n",
            "error": None,
        },
        "selinux_status": {"type": "command", "command": "x", "raw_output": "Enforcing\n", "error": None},
        "legacy_firewall_status": {
            "type": "command",
            "command": "x",
            "raw_output": "__FIREWALLD__\nactive\n__UFW__\ninactive\n__IPTABLES__\nChain INPUT (policy ACCEPT)\n",
            "error": None,
        },
        "legacy_open_ports": {
            "type": "command",
            "command": "x",
            "raw_output": "tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\ntcp LISTEN 0 128 0.0.0.0:80 0.0.0.0:*\n",
            "error": None,
        },
        "pam_pwquality_config": {
            "type": "config",
            "command": "x",
            "raw_output": "minlen = 12\nminclass = 3\npassword requisite pam_pwquality.so retry=3\n",
            "error": None,
        },
        "pam_faillock_config": {
            "type": "config",
            "command": "x",
            "raw_output": "auth required pam_faillock.so preauth deny=5 unlock_time=900\n",
            "error": None,
        },
        "audit_log_permissions": {
            "type": "command",
            "command": "x",
            "raw_output": "/var/log/audit 750 root root\n/var/log/audit/audit.log 640 root root\n",
            "error": None,
        },
        "audit_process_status": {"type": "command", "command": "x", "raw_output": "enabled 1\n", "error": None},
        "interactive_system_accounts": {"type": "config", "command": "x", "raw_output": "", "error": None},
        "interactive_user_accounts": {
            "type": "config",
            "command": "x",
            "raw_output": "ops:1000:/bin/bash\n",
            "error": None,
        },
        "enabled_services": {
            "type": "command",
            "command": "x",
            "raw_output": "sshd.service enabled\nchronyd.service enabled\n",
            "error": None,
        },
        "hosts_access_control": {
            "type": "config",
            "command": "x",
            "raw_output": "__ALLOW__\nsshd: 10.0.0.0/24\n__DENY__\nALL: ALL\n",
            "error": None,
        },
        "package_updates": {
            "type": "command",
            "command": "x",
            "raw_output": "Listing...\nopenssl/stable 3.0.2 upgradable from: 3.0.1\n",
            "error": None,
        },
        "ids_presence": {
            "type": "command",
            "command": "x",
            "raw_output": "root 1 0 00:00 ? 00:00:01 wazuh-agentd\n",
            "error": None,
        },
    }


def test_linux_baseline_engine_reduces_unknown_for_clear_missing_or_updatable_signals() -> None:
    engine = LinuxBaselineRuleEngine()

    results = engine.evaluate_linux_inspection(
        {
            "collected_data": {
                "selinux_status": _collected_entry("unavailable\n"),
                "pam_pwquality_config": _collected_entry(""),
                "pam_faillock_config": _collected_entry(""),
                "audit_log_permissions": _collected_entry(""),
                "audit_process_status": _collected_entry("unavailable\n"),
                "hosts_access_control": _collected_entry(
                    "\n__ALLOW__\n# default comment\n\n__DENY__\n# default comment\n\n__SSHD__\n"
                ),
                "package_updates": _collected_entry(
                    "Listing... Done\nopenssl/stable-security 3.0.2 amd64 [upgradable from: 3.0.1]\n"
                ),
            }
        }
    )

    results_by_id = {item.rule_id: item for item in results}

    assert results_by_id["linux_selinux_enforcing"].status == "fail"
    assert results_by_id["linux_pam_password_complexity"].status == "fail"
    assert results_by_id["linux_login_failure_lock"].status == "fail"
    assert results_by_id["linux_audit_log_protection"].status == "fail"
    assert results_by_id["linux_audit_process_protection"].status == "fail"
    assert results_by_id["linux_management_ip_restriction"].status == "fail"
    assert results_by_id["linux_patch_update_status"].status == "fail"
    assert "openssl/stable-security" in results_by_id["linux_patch_update_status"].evidence


def test_linux_baseline_engine_accepts_explicit_management_source_restrictions() -> None:
    engine = LinuxBaselineRuleEngine()

    results = engine.evaluate_linux_inspection(
        {
            "collected_data": {
                "hosts_access_control": _collected_entry(
                    "\n__ALLOW__\nsshd: 10.0.0.0/24\n\n__DENY__\nALL: ALL\n\n__SSHD__\nAllowUsers ops@10.0.0.*\n"
                )
            }
        }
    )

    results_by_id = {item.rule_id: item for item in results}

    assert results_by_id["linux_management_ip_restriction"].status == "pass"


def test_linux_baseline_engine_compacts_noisy_package_update_output() -> None:
    engine = LinuxBaselineRuleEngine()

    results = engine.evaluate_linux_inspection(
        {
            "collected_data": {
                "package_updates": _collected_entry(
                    "[=== ] --- B/s | 0 B ETA 00:00 everything\n"
                    "--- B/s | 0 B ETA 00:00 NetworkManager.x86_64\n"
                    "update NetworkManager.x86_64 1:1.44.2-6.oe2403sp1 "
                    "update NetworkManager-config-server.noarch 1:1.44.2-6.oe2403sp1 "
                    "update audit.x86_64 4:3.1.2-9.oe2403sp1\n"
                )
            }
        }
    )

    results_by_id = {item.rule_id: item for item in results}
    package_result = results_by_id["linux_patch_update_status"]

    assert package_result.status == "fail"
    assert "NetworkManager.x86_64 -> 1:1.44.2-6.oe2403sp1" in package_result.evidence
    assert "NetworkManager-config-server.noarch -> 1:1.44.2-6.oe2403sp1" in package_result.evidence
    assert "audit.x86_64 -> 4:3.1.2-9.oe2403sp1" in package_result.evidence
    assert "ETA" not in package_result.evidence


def _linux_rate_limit_capacity() -> int:
    return int(get_settings().linux_inspection_rate_limit.split("/", maxsplit=1)[0])


def test_run_linux_inspection_saves_success_result(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(
            success=True,
            message="Linux inspection completed",
            open_ports=OpenPortsResult(
                ports=[
                    OpenPortEntry(protocol="tcp", local_address="0.0.0.0", port="22", state="LISTEN"),
                    OpenPortEntry(protocol="tcp", local_address="0.0.0.0", port="80", state="LISTEN"),
                ],
                raw_output="tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\ntcp LISTEN 0 128 0.0.0.0:80 0.0.0.0:*",
            ),
            ssh_config=SSHConfigResult(
                settings={
                    "port": "22",
                    "permitrootlogin": "no",
                    "passwordauthentication": "yes",
                },
                raw_output="port 22\npermitrootlogin no\npasswordauthentication yes",
            ),
            firewall_status=FirewallStatusResult(
                firewalld="active",
                ufw="inactive",
                iptables_rules=["Chain INPUT (policy ACCEPT)"],
                raw_output="__FIREWALLD__\nactive\n__UFW__\ninactive\n__IPTABLES__\nChain INPUT (policy ACCEPT)",
            ),
            time_sync_status=TimeSyncStatusResult(
                timedatectl="System clock synchronized: yes\nNTP service: active",
                service_status="active",
                raw_output="__TIMEDATECTL__\nSystem clock synchronized: yes\nNTP service: active\n__SERVICE__\nactive",
            ),
            auditd_status=AuditdStatusResult(
                service_status="active",
                auditctl_status="enabled 1",
                raw_output="__AUDITD__\nactive\n__AUDITCTL__\nenabled 1",
            ),
            collected_data=_build_collected_data(),
        )
    )

    response = client.post(
        "/api/v1/linux-inspections/run",
        json={
            "ip": "192.168.56.10",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["ip"] == "192.168.56.10"
    assert payload["username"] == "root"
    assert payload["success"] is True
    assert payload["open_ports"]["ports"][0]["port"] == "22"
    assert payload["ssh_config"]["settings"]["permitrootlogin"] == "no"
    assert payload["firewall_status"]["firewalld"] == "active"
    assert payload["time_sync_status"]["service_status"] == "active"
    assert payload["auditd_status"]["service_status"] == "active"
    assert payload["collected_data"]["shadow_empty_passwords"]["raw_output"] == ""
    assert len(payload["baseline_results"]) == 27

    results_by_id = {item["rule_id"]: item for item in payload["baseline_results"]}
    assert results_by_id["linux_empty_password_accounts"]["status"] == "pass"
    assert results_by_id["linux_firewall_enabled"]["status"] == "pass"
    assert results_by_id["linux_sudo_nopasswd_absent"]["status"] == "fail"
    assert results_by_id["linux_dual_factor_authentication"]["status"] == "unknown"
    assert results_by_id["linux_data_validity_check"]["status"] == "not_applicable"
    assert results_by_id["linux_sudo_nopasswd_absent"]["evidence"] != ""
    assert results_by_id["linux_dual_factor_authentication"]["manual_check_hint"] is not None

    list_response = client.get("/api/v1/linux-inspections")
    assert list_response.status_code == 200
    inspections = list_response.json()
    assert len(inspections) == 1
    assert inspections[0]["id"] == payload["id"]
    assert len(inspections[0]["baseline_results"]) == 27


def test_run_linux_inspection_saves_failure_result(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=False, message="SSH authentication failed")
    )

    response = client.post(
        "/api/v1/linux-inspections/run",
        json={
            "ip": "192.168.56.11",
            "username": "admin",
            "password": "wrong-password",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is False
    assert payload["message"] == "SSH authentication failed"
    assert payload["open_ports"] is None
    assert payload["ssh_config"] is None
    assert payload["firewall_status"] is None
    assert payload["time_sync_status"] is None
    assert payload["auditd_status"] is None
    assert len(payload["baseline_results"]) == 27
    assert {item["status"] for item in payload["baseline_results"]} == {"unknown", "not_applicable"}


def test_run_linux_inspection_links_existing_asset_without_transaction_conflict(client) -> None:
    create_asset_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.56.12",
            "type": "linux",
            "name": "prod-web-12",
            "username": "root",
            "credential_password": "linux-secret",
        },
    )
    assert create_asset_response.status_code == 201
    asset = create_asset_response.json()

    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(
            success=True,
            message="Linux inspection completed",
            open_ports=OpenPortsResult(
                ports=[OpenPortEntry(protocol="tcp", local_address="0.0.0.0", port="22", state="LISTEN")],
                raw_output="tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*",
            ),
            ssh_config=SSHConfigResult(
                settings={"port": "22", "permitrootlogin": "no"},
                raw_output="port 22\npermitrootlogin no",
            ),
            firewall_status=FirewallStatusResult(
                firewalld="active",
                ufw="inactive",
                iptables_rules=["Chain INPUT (policy ACCEPT)"],
                raw_output="__FIREWALLD__\nactive\n__UFW__\ninactive\n__IPTABLES__\nChain INPUT (policy ACCEPT)",
            ),
            time_sync_status=TimeSyncStatusResult(
                timedatectl="System clock synchronized: yes\nNTP service: active",
                service_status="active",
                raw_output="__TIMEDATECTL__\nSystem clock synchronized: yes\nNTP service: active\n__SERVICE__\nactive",
            ),
            auditd_status=AuditdStatusResult(
                service_status="active",
                auditctl_status="enabled 1",
                raw_output="__AUDITD__\nactive\n__AUDITCTL__\nenabled 1",
            ),
            collected_data=_build_collected_data(),
        )
    )

    response = client.post(
        "/api/v1/linux-inspections/run",
        json={
            "ip": asset["ip"],
            "username": "root",
            "password": "linux-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]


def test_list_linux_inspections_supports_pagination(client) -> None:
    inspector = lambda ip_suffix: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message=f"Linux inspection {ip_suffix}")
    )

    for index in range(3):
        client.app.dependency_overrides[get_linux_inspector] = lambda index=index: inspector(index)
        response = client.post(
            "/api/v1/linux-inspections/run",
            json={
                "ip": f"192.168.56.3{index}",
                "username": "root",
                "password": "super-secret",
            },
        )
        assert response.status_code == 201

    client.app.dependency_overrides.clear()

    response = client.get("/api/v1/linux-inspections?skip=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ip"] == "192.168.56.31"


def test_linux_inspection_password_is_not_logged(client, caplog) -> None:
    secret = "DontLogThisPassword!"
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message="Linux inspection completed")
    )

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/linux-inspections/run",
            json={
                "ip": "192.168.56.12",
                "username": "ops",
                "password": secret,
            },
        )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert secret not in caplog.text


def test_linux_inspection_request_trims_ip_whitespace(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message="Linux inspection completed")
    )

    response = client.post(
        "/api/v1/linux-inspections/run",
        json={
            "ip": " 192.168.56.14 ",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["ip"] == "192.168.56.14"


def test_openapi_exposes_linux_inspection_endpoints(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/linux-inspections/run" in openapi["paths"]
    assert "/api/v1/linux-inspections" in openapi["paths"]
    parameter_names = {
        item["name"] for item in openapi["paths"]["/api/v1/linux-inspections"]["get"]["parameters"]
    }
    assert {"skip", "limit"} <= parameter_names


def test_linux_inspection_rate_limit_returns_429(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message="Linux inspection completed")
    )

    for _ in range(_linux_rate_limit_capacity()):
        response = client.post(
            "/api/v1/linux-inspections/run",
            json={
                "ip": "192.168.56.13",
                "username": "root",
                "password": "super-secret",
            },
        )
        assert response.status_code == 201

    limited_response = client.post(
        "/api/v1/linux-inspections/run",
        json={
            "ip": "192.168.56.13",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limit_exceeded"


def test_linux_inspection_rolls_back_when_baseline_save_fails(client, monkeypatch) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message="Linux inspection completed")
    )

    async def broken_add_for_linux_inspection(self, *, linux_inspection_id: int, results):
        raise RuntimeError("baseline write failed")

    monkeypatch.setattr(
        BaselineCheckResultRepository,
        "add_for_linux_inspection",
        broken_add_for_linux_inspection,
    )

    with pytest.raises(RuntimeError, match="baseline write failed"):
        client.post(
            "/api/v1/linux-inspections/run",
            json={
                "ip": "192.168.56.15",
                "username": "root",
                "password": "super-secret",
            },
        )

    client.app.dependency_overrides.clear()
    monkeypatch.undo()

    list_response = client.get("/api/v1/linux-inspections")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_linux_inspector_uses_timeouts_from_settings() -> None:
    inspector = get_linux_inspector(
        Settings(
            ssh_connection_timeout_seconds=17,
            ssh_command_read_timeout_seconds=180,
        )
    )

    assert inspector.connection_timeout_seconds == 17
    assert inspector.command_read_timeout_seconds == 180


def test_linux_inspector_logs_unexpected_errors(monkeypatch, caplog) -> None:
    secret = "LinuxSecretShouldStayHidden!"

    def raise_runtime_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(linux_client_module, "ConnectHandler", raise_runtime_error)

    with caplog.at_level(logging.ERROR):
        result = linux_client_module.LinuxInspectorClient(
            connection_timeout_seconds=10,
            command_read_timeout_seconds=120,
        ).inspect(
            ip="192.168.56.14",
            username="root",
            password=secret,
        )

    assert result == LinuxInspectionExecution(success=False, message="Linux inspection failed")
    assert "Unexpected Linux inspection error" in caplog.text
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text


class FakeTerminalConnection:
    def __init__(self, output: str) -> None:
        self.output = output
        self.commands: list[str] = []

    def send_command(self, command: str, *, strip_prompt: bool, strip_command: bool, read_timeout: int) -> str:
        self.commands.append(command)
        return self.output


def test_linux_inspector_collect_normalizes_terminal_output() -> None:
    inspector = linux_client_module.LinuxInspectorClient()
    connection = FakeTerminalConnection("\u001b[?2004lport 22\r\npermitrootlogin no\r\n")

    collected_data = inspector._collect(
        connection=connection,
        collection_plan=[LinuxCollectCommand(key="ssh_config", collect_type="command", command="cat /etc/ssh/sshd_config")],
    )

    assert collected_data["ssh_config"]["raw_output"] == "\u001b[?2004lport 22\r\npermitrootlogin no\r\n"
    assert collected_data["ssh_config"]["normalized_output"] == "port 22\npermitrootlogin no\n"
    assert inspector._get_output(collected_data, "ssh_config") == "port 22\npermitrootlogin no\n"


def test_linux_inspector_collect_strips_exit_status_marker() -> None:
    inspector = linux_client_module.LinuxInspectorClient()
    connection = FakeTerminalConnection("port 22\n__XUNJIAN_EXIT_STATUS__:0\n")

    collected_data = inspector._collect(
        connection=connection,
        collection_plan=[LinuxCollectCommand(key="ssh_config", collect_type="command", command="cat /etc/ssh/sshd_config")],
    )

    assert "2>&1" in connection.commands[0]
    assert "__XUNJIAN_EXIT_STATUS__" in connection.commands[0]
    assert collected_data["ssh_config"]["raw_output"] == "port 22"
    assert collected_data["ssh_config"]["normalized_output"] == "port 22"
    assert collected_data["ssh_config"]["error"] is None


def test_linux_inspector_collect_marks_legacy_empty_failure_as_error() -> None:
    inspector = linux_client_module.LinuxInspectorClient()
    connection = FakeTerminalConnection("__XUNJIAN_EXIT_STATUS__:127\n")

    collected_data = inspector._collect(
        connection=connection,
        collection_plan=[LinuxCollectCommand(key="legacy_open_ports", collect_type="command", command="ss -tulnH 2>&1")],
    )

    assert collected_data["legacy_open_ports"]["raw_output"] == ""
    assert collected_data["legacy_open_ports"]["normalized_output"] == ""
    assert collected_data["legacy_open_ports"]["error"] == "Command exited with status 127"


def test_linux_rule_engine_prefers_normalized_output_for_evidence() -> None:
    engine = LinuxBaselineRuleEngine()
    inspection = {
        "success": True,
        "message": "Linux inspection completed",
        "collected_data": {
            "uid0_accounts": {
                "type": "config",
                "command": "awk -F: '$3 == 0 {print $1}' /etc/passwd",
                "raw_output": "\u001b[?2004lroot\n",
                "normalized_output": "root\n",
                "error": None,
            }
        },
    }

    result = next(item for item in engine.evaluate_linux_inspection(inspection) if item.rule_id == "linux_uid0_unique_root")

    assert result.status == "pass"
    assert "\u001b" not in result.evidence
    assert result.evidence == "仅 root 具备 UID 0"


def test_linux_rule_engine_accepts_ssh_alias_service_state() -> None:
    engine = LinuxBaselineRuleEngine()
    inspection = {
        "success": True,
        "message": "Linux inspection completed",
        "collected_data": {
            "ssh_service_state": {
                "type": "command",
                "command": "systemctl is-enabled ssh && systemctl is-active ssh",
                "raw_output": "alias\nactive\n",
                "normalized_output": "alias\nactive\n",
                "error": None,
            }
        },
    }

    result = next(
        item for item in engine.evaluate_linux_inspection(inspection) if item.rule_id == "linux_ssh_service_enabled"
    )

    assert result.status == "pass"
    assert result.evidence == "enabled=alias, active=active"
