import logging

import pytest

from app.core.config import Settings
from app.core.config import get_settings
from app.features.baseline.repository import BaselineCheckResultRepository
from app.features.switch_inspections import client as switch_client_module
from app.features.switch_inspections.client import SwitchInspectionResult
from app.features.switch_inspections.router import get_h3c_switch_inspector


class FakeH3CSwitchInspector:
    def __init__(self, result: SwitchInspectionResult) -> None:
        self.result = result

    def inspect(self, *, ip: str, username: str, password: str, port: int = 22) -> SwitchInspectionResult:
        return self.result


def _switch_rate_limit_capacity() -> int:
    return int(get_settings().switch_inspection_rate_limit.split("/", maxsplit=1)[0])


def test_run_h3c_switch_inspection_success(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(
            success=True,
            message="H3C switch inspection completed",
            raw_config="\n".join(
                [
                    "sysname CORE-SW-01",
                    "undo telnet server enable",
                    "stelnet server enable",
                    "ntp-service unicast-server 192.168.10.10",
                    "info-center loghost 192.168.10.20 facility local7",
                    "aaa",
                    " local-user admin class manage",
                ]
            ),
        )
    )

    response = client.post(
        "/api/v1/switch-inspections/h3c/run",
        json={
            "ip": "192.168.10.2",
            "username": "admin",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["vendor"] == "H3C"
    assert payload["message"] == "H3C switch inspection completed"
    assert payload["ip"] == "192.168.10.2"
    assert payload["username"] == "admin"
    assert payload["id"] > 0
    assert len(payload["baseline_results"]) == 5
    assert {item["status"] for item in payload["baseline_results"]} == {"pass"}

    list_response = client.get("/api/v1/switch-inspections/h3c")
    assert list_response.status_code == 200
    inspections = list_response.json()
    assert len(inspections) == 1
    assert inspections[0]["id"] == payload["id"]
    assert len(inspections[0]["baseline_results"]) == 5


def test_run_switch_inspection_success_via_unified_route(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(
            success=True,
            message="H3C switch inspection completed",
            raw_config="sysname CORE-SW-02\nstelnet server enable",
        )
    )

    response = client.post(
        "/api/v1/switch-inspections/run",
        json={
            "ip": "192.168.10.7",
            "username": "admin",
            "password": "super-secret",
            "vendor": "h3c",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["vendor"] == "H3C"
    assert payload["ip"] == "192.168.10.7"

    list_response = client.get("/api/v1/switch-inspections")
    assert list_response.status_code == 200
    inspections = list_response.json()
    assert len(inspections) == 1
    assert inspections[0]["id"] == payload["id"]


def test_run_switch_inspection_links_existing_asset_without_transaction_conflict(client) -> None:
    create_asset_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.10.8",
            "type": "switch",
            "name": "core-sw-08",
            "username": "admin",
            "vendor": "h3c",
            "credential_password": "switch-secret",
        },
    )
    assert create_asset_response.status_code == 201
    asset = create_asset_response.json()

    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(
            success=True,
            message="H3C switch inspection completed",
            raw_config="sysname CORE-SW-08\nstelnet server enable",
        )
    )

    response = client.post(
        "/api/v1/switch-inspections/run",
        json={
            "ip": asset["ip"],
            "username": "admin",
            "password": "switch-secret",
            "vendor": "h3c",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["asset_id"] == asset["id"]


def test_run_h3c_switch_inspection_failure(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(success=False, message="SSH authentication failed")
    )

    response = client.post(
        "/api/v1/switch-inspections/h3c/run",
        json={
            "ip": "192.168.10.3",
            "username": "admin",
            "password": "wrong-password",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["vendor"] == "H3C"
    assert payload["message"] == "SSH authentication failed"
    assert payload["raw_config"] is None
    assert len(payload["baseline_results"]) == 5
    assert {item["status"] for item in payload["baseline_results"]} == {"unknown"}
    status_by_rule = {item["rule_id"]: item["status"] for item in payload["baseline_results"]}
    assert status_by_rule["switch_telnet_disabled"] == "unknown"
    assert status_by_rule["switch_ssh_enabled"] == "unknown"
    assert status_by_rule["switch_ntp_configured"] == "unknown"
    assert status_by_rule["switch_syslog_configured"] == "unknown"
    assert status_by_rule["switch_aaa_configured"] == "unknown"


def test_list_h3c_switch_inspections_supports_pagination(client) -> None:
    for index in range(3):
        client.app.dependency_overrides[get_h3c_switch_inspector] = lambda index=index: FakeH3CSwitchInspector(
            SwitchInspectionResult(success=True, message=f"H3C switch inspection {index}", raw_config=f"sysname CORE-{index}")
        )
        response = client.post(
            "/api/v1/switch-inspections/h3c/run",
            json={
                "ip": f"192.168.10.1{index}",
                "username": "admin",
                "password": "super-secret",
            },
        )
        assert response.status_code == 200

    client.app.dependency_overrides.clear()

    response = client.get("/api/v1/switch-inspections/h3c?skip=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ip"] == "192.168.10.11"
    assert payload[0]["vendor"] == "H3C"


def test_h3c_switch_password_is_not_logged(client, caplog) -> None:
    secret = "DoNotLogSwitchPassword!"
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(success=True, message="H3C switch inspection completed", raw_config="sysname CORE")
    )

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/switch-inspections/h3c/run",
            json={
                "ip": "192.168.10.4",
                "username": "netops",
                "password": secret,
            },
        )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert secret not in caplog.text


def test_switch_inspection_request_trims_ip_whitespace(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(success=True, message="H3C switch inspection completed", raw_config="sysname CORE")
    )

    response = client.post(
        "/api/v1/switch-inspections/run",
        json={
            "ip": " 192.168.10.9 ",
            "username": "admin",
            "password": "super-secret",
            "vendor": "h3c",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ip"] == "192.168.10.9"


def test_openapi_exposes_h3c_switch_endpoint(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/switch-inspections/run" in openapi["paths"]
    assert "/api/v1/switch-inspections" in openapi["paths"]
    assert "/api/v1/switch-inspections/h3c/run" in openapi["paths"]
    assert "/api/v1/switch-inspections/h3c" in openapi["paths"]
    list_parameter_names = {
        item["name"] for item in openapi["paths"]["/api/v1/switch-inspections"]["get"]["parameters"]
    }
    h3c_parameter_names = {
        item["name"] for item in openapi["paths"]["/api/v1/switch-inspections/h3c"]["get"]["parameters"]
    }
    assert {"skip", "limit"} <= list_parameter_names
    assert {"skip", "limit"} <= h3c_parameter_names


def test_h3c_switch_inspection_rate_limit_returns_429(client) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(success=True, message="H3C switch inspection completed", raw_config="sysname CORE")
    )

    for _ in range(_switch_rate_limit_capacity()):
        response = client.post(
            "/api/v1/switch-inspections/run",
            json={
                "ip": "192.168.10.5",
                "username": "admin",
                "password": "super-secret",
                "vendor": "h3c",
            },
        )
        assert response.status_code == 200

    limited_response = client.post(
        "/api/v1/switch-inspections/run",
        json={
            "ip": "192.168.10.5",
            "username": "admin",
            "password": "super-secret",
            "vendor": "h3c",
        },
    )

    client.app.dependency_overrides.clear()

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limit_exceeded"


def test_switch_inspection_rolls_back_when_baseline_save_fails(client, monkeypatch) -> None:
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(success=True, message="H3C switch inspection completed", raw_config="sysname CORE")
    )

    async def broken_add_for_switch_inspection(self, *, switch_inspection_id: int, results):
        raise RuntimeError("baseline write failed")

    monkeypatch.setattr(
        BaselineCheckResultRepository,
        "add_for_switch_inspection",
        broken_add_for_switch_inspection,
    )

    with pytest.raises(RuntimeError, match="baseline write failed"):
        client.post(
            "/api/v1/switch-inspections/run",
            json={
                "ip": "192.168.10.8",
                "username": "admin",
                "password": "super-secret",
                "vendor": "h3c",
            },
        )

    client.app.dependency_overrides.clear()
    monkeypatch.undo()

    list_response = client.get("/api/v1/switch-inspections")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_h3c_switch_inspector_uses_timeouts_from_settings() -> None:
    inspector = get_h3c_switch_inspector(
        Settings(
            ssh_connection_timeout_seconds=19,
            ssh_command_read_timeout_seconds=240,
        )
    )

    assert inspector.connection_timeout_seconds == 19
    assert inspector.command_read_timeout_seconds == 240


def test_h3c_switch_inspector_logs_unexpected_errors(monkeypatch, caplog) -> None:
    secret = "SwitchSecretShouldStayHidden!"

    def raise_runtime_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(switch_client_module, "ConnectHandler", raise_runtime_error)

    with caplog.at_level(logging.ERROR):
        result = switch_client_module.H3CSwitchInspectorClient(
            connection_timeout_seconds=10,
            command_read_timeout_seconds=120,
        ).inspect(
            ip="192.168.10.6",
            username="admin",
            password=secret,
        )

    assert result == SwitchInspectionResult(success=False, message="H3C switch inspection failed")
    assert "Unexpected H3C switch inspection error" in caplog.text
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text
