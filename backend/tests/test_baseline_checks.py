from pathlib import Path

from app.features.baseline.engine import BaselineRuleEngine, load_rules
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
from app.features.switch_inspections.client import SwitchInspectionResult
from app.features.switch_inspections.router import get_h3c_switch_inspector


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


class FakeH3CSwitchInspector:
    def __init__(self, result: SwitchInspectionResult) -> None:
        self.result = result

    def inspect(self, *, ip: str, username: str, password: str, port: int = 22) -> SwitchInspectionResult:
        return self.result


def test_run_linux_baseline_independently(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(
            success=True,
            message="Linux inspection completed",
            open_ports=OpenPortsResult(
                ports=[OpenPortEntry(protocol="tcp", local_address="0.0.0.0", port="22", state="LISTEN")],
                raw_output="tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:*",
            ),
            ssh_config=SSHConfigResult(
                settings={"permitrootlogin": "no", "passwordauthentication": "no"},
                raw_output="permitrootlogin no\npasswordauthentication no",
            ),
            firewall_status=FirewallStatusResult(
                firewalld="active",
                ufw="inactive",
                iptables_rules=["Chain INPUT (policy ACCEPT)"],
                raw_output="active",
            ),
            time_sync_status=TimeSyncStatusResult(
                timedatectl="System clock synchronized: yes",
                service_status="active",
                raw_output="System clock synchronized: yes",
            ),
            auditd_status=AuditdStatusResult(
                service_status="active",
                auditctl_status="enabled 1",
                raw_output="enabled 1",
            ),
            collected_data={
                "shadow_empty_passwords": {"type": "command", "command": "x", "raw_output": "", "error": None},
                "login_defs_pass_max_days": {"type": "config", "command": "x", "raw_output": "90\n", "error": None},
                "telnet_service_state": {"type": "command", "command": "x", "raw_output": "disabled\ninactive\n", "error": None},
                "ssh_service_state": {"type": "command", "command": "x", "raw_output": "enabled\nactive\n", "error": None},
                "legacy_auditd_status": {"type": "command", "command": "x", "raw_output": "__AUDITD__\nactive\n__AUDITCTL__\nenabled 1\n", "error": None},
                "uid0_accounts": {"type": "config", "command": "x", "raw_output": "root\n", "error": None},
                "sudoers_risky_entries": {"type": "config", "command": "x", "raw_output": "", "error": None},
                "passwd_shadow_permissions": {"type": "config", "command": "x", "raw_output": "/etc/passwd 644 root root\n/etc/shadow 640 root shadow\n", "error": None},
                "selinux_status": {"type": "command", "command": "x", "raw_output": "Enforcing\n", "error": None},
                "legacy_firewall_status": {"type": "command", "command": "x", "raw_output": "", "error": None},
                "legacy_open_ports": {"type": "command", "command": "x", "raw_output": "", "error": None},
                "pam_pwquality_config": {"type": "config", "command": "x", "raw_output": "minlen = 12\npassword requisite pam_pwquality.so retry=3\n", "error": None},
                "pam_faillock_config": {"type": "config", "command": "x", "raw_output": "auth required pam_faillock.so preauth deny=5 unlock_time=900\n", "error": None},
                "audit_log_permissions": {"type": "command", "command": "x", "raw_output": "/var/log/audit 750 root root\n/var/log/audit/audit.log 640 root root\n", "error": None},
                "audit_process_status": {"type": "command", "command": "x", "raw_output": "enabled 2\n", "error": None},
                "interactive_system_accounts": {"type": "config", "command": "x", "raw_output": "", "error": None},
                "interactive_user_accounts": {"type": "config", "command": "x", "raw_output": "ops:1000:/bin/bash\n", "error": None},
                "enabled_services": {"type": "command", "command": "x", "raw_output": "sshd.service enabled\n", "error": None},
                "hosts_access_control": {"type": "config", "command": "x", "raw_output": "__ALLOW__\nsshd: 10.0.0.0/24\n__DENY__\nALL: ALL\n", "error": None},
                "package_updates": {"type": "command", "command": "x", "raw_output": "0 upgraded, 0 newly installed\n", "error": None},
                "ids_presence": {"type": "command", "command": "x", "raw_output": "root 1 0 00:00 ? 00:00:01 wazuh-agentd\n", "error": None},
            },
        )
    )

    response = client.post(
        "/api/v1/baseline-checks/linux/run",
        json={
            "ip": "192.168.56.21",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_type"] == "linux_inspection"
    assert payload["device_type"] == "linux"
    assert payload["ip"] == "192.168.56.21"
    assert payload["inspection_id"] > 0
    assert len(payload["baseline_results"]) == 27
    results_by_id = {item["rule_id"]: item for item in payload["baseline_results"]}
    assert results_by_id["linux_empty_password_accounts"]["status"] == "pass"
    assert results_by_id["linux_data_validity_check"]["status"] == "not_applicable"

    list_response = client.get("/api/v1/baseline-checks")
    assert list_response.status_code == 200
    runs = list_response.json()
    assert len(runs) == 1
    assert runs[0]["inspection_id"] == payload["inspection_id"]


def test_rerun_linux_baseline_replaces_existing_results(client) -> None:
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(
            success=False,
            message="SSH authentication failed",
        )
    )

    first_response = client.post(
        "/api/v1/baseline-checks/linux/run",
        json={
            "ip": "192.168.56.22",
            "username": "root",
            "password": "wrong-password",
        },
    )
    assert first_response.status_code == 201
    inspection_id = first_response.json()["inspection_id"]

    rerun_response = client.post(f"/api/v1/baseline-checks/linux/{inspection_id}/rerun")

    client.app.dependency_overrides.clear()

    assert rerun_response.status_code == 200
    rerun_payload = rerun_response.json()
    assert len(rerun_payload["baseline_results"]) == 27

    inspections_response = client.get("/api/v1/linux-inspections")
    assert inspections_response.status_code == 200
    inspections = inspections_response.json()
    assert len(inspections) == 1
    assert len(inspections[0]["baseline_results"]) == 27


def test_run_switch_baseline_independently(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(
            success=True,
            message="H3C switch inspection completed",
            raw_config="undo telnet server enable\nstelnet server enable\nntp-service unicast-server 1.1.1.1\naaa",
        )
    )

    response = client.post(
        "/api/v1/baseline-checks/switch/run",
        json={
            "ip": "192.168.10.31",
            "username": "admin",
            "password": "super-secret",
            "vendor": "h3c",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_type"] == "switch_inspection"
    assert payload["device_type"] == "switch"
    assert payload["vendor"] == "H3C"
    assert payload["inspection_id"] > 0
    assert len(payload["baseline_results"]) == 5


def test_openapi_exposes_baseline_endpoints(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/baseline-checks" in openapi["paths"]
    assert "/api/v1/baseline-checks/linux/run" in openapi["paths"]
    assert "/api/v1/baseline-checks/switch/run" in openapi["paths"]
    assert "/api/v1/baseline-checks/linux/{inspection_id}/rerun" in openapi["paths"]
    assert "/api/v1/baseline-checks/switch/{inspection_id}/rerun" in openapi["paths"]


def test_baseline_engine_supports_registered_operator_and_custom_rules_path(tmp_path: Path) -> None:
    custom_rules_path = tmp_path / "custom_rules.json"
    custom_rules_path.write_text(
        """
        [
          {
            "rule_id": "linux_custom_operator",
            "name": "Custom operator",
            "device_type": "linux",
            "risk_level": "medium",
            "check_method": "config",
            "judge_logic": "Use custom matcher",
            "matcher": {
              "operator": "starts_with",
              "source": "message",
              "expected_prefix": "Linux"
            },
            "remediation": "Keep the prefix"
          }
        ]
        """.strip(),
        encoding="utf-8",
    )

    engine = BaselineRuleEngine(rules=load_rules(custom_rules_path))
    engine.register_operator(
        "starts_with",
        lambda matcher, inspection: (
            "pass",
            f"Observed prefix {matcher['expected_prefix']}",
        )
        if str(inspection.get(matcher["source"], "")).startswith(matcher["expected_prefix"])
        else ("fail", "Prefix mismatch"),
    )

    results = engine.evaluate_linux_inspection({"message": "Linux inspection completed"})

    assert len(results) == 1
    assert results[0].rule_id == "linux_custom_operator"
    assert results[0].status == "pass"
