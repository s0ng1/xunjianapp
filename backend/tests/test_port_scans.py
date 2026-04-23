import asyncio
import logging

import pytest

from app.core.config import Settings
from app.core.config import get_settings
from app.features.port_scans import client as port_scan_client_module
from app.features.port_scans.client import PortScanExecution
from app.features.port_scans.router import get_port_scanner
from app.features.port_scans.repository import PortScanRepository
from app.features.port_scans.schemas import PortScanPortState


class FakePortScanner:
    def __init__(self, execution: PortScanExecution) -> None:
        self.execution = execution

    async def scan(self, *, ip: str, ports: list[int] | None = None) -> PortScanExecution:
        return self.execution


def _port_scan_rate_limit_capacity() -> int:
    return int(get_settings().port_scan_rate_limit.split("/", maxsplit=1)[0])


def test_run_port_scan_saves_success_result(client) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 2 open of 3 checked",
            checked_ports=[22, 80, 443],
            open_ports=[
                PortScanPortState(port=22, is_open=True),
                PortScanPortState(port=443, is_open=True),
            ],
        )
    )

    response = client.post(
        "/api/v1/port-scans/run",
        json={
            "ip": "192.168.56.20",
            "ports": [22, 80, 443],
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["ip"] == "192.168.56.20"
    assert payload["success"] is True
    assert payload["checked_ports"] == [22, 80, 443]
    assert payload["open_ports"] == [
        {"protocol": "tcp", "port": 22, "is_open": True},
        {"protocol": "tcp", "port": 443, "is_open": True},
    ]

    list_response = client.get("/api/v1/port-scans")
    assert list_response.status_code == 200
    scans = list_response.json()
    assert len(scans) == 1
    assert scans[0]["id"] == payload["id"]


def test_run_port_scan_uses_server_defaults_when_ports_are_omitted(client) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 2 checked",
            checked_ports=[22, 443],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    response = client.post(
        "/api/v1/port-scans/run",
        json={"ip": "192.168.56.21"},
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["checked_ports"] == [22, 443]


def test_run_port_scan_links_existing_asset_without_transaction_conflict(client) -> None:
    create_asset_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.56.26",
            "type": "linux",
            "name": "prod-web-26",
            "username": "root",
            "credential_password": "linux-secret",
        },
    )
    assert create_asset_response.status_code == 201
    asset = create_asset_response.json()

    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 2 checked",
            checked_ports=[22, 443],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    response = client.post(
        "/api/v1/port-scans/run",
        json={"ip": asset["ip"], "ports": [22, 443]},
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]


def test_port_scan_validation_deduplicates_ports(client) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 2 checked",
            checked_ports=[22, 443],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    response = client.post(
        "/api/v1/port-scans/run",
        json={"ip": "192.168.56.22", "ports": [22, 22, 443]},
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["checked_ports"] == [22, 443]


def test_port_scan_request_trims_ip_whitespace(client) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 1 checked",
            checked_ports=[22],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    response = client.post(
        "/api/v1/port-scans/run",
        json={"ip": " 192.168.56.29 ", "ports": [22]},
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["ip"] == "192.168.56.29"


def test_list_port_scans_supports_pagination(client) -> None:
    for index in range(3):
        client.app.dependency_overrides[get_port_scanner] = lambda index=index: FakePortScanner(
            PortScanExecution(
                success=True,
                message=f"Port scan completed: {index}",
                checked_ports=[22],
                open_ports=[PortScanPortState(port=22, is_open=True)],
            )
        )
        response = client.post(
            "/api/v1/port-scans/run",
            json={"ip": f"192.168.56.4{index}", "ports": [22]},
        )
        assert response.status_code == 201

    client.app.dependency_overrides.clear()

    response = client.get("/api/v1/port-scans?skip=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ip"] == "192.168.56.41"


def test_openapi_exposes_port_scan_endpoints(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/port-scans/run" in openapi["paths"]
    assert "/api/v1/port-scans" in openapi["paths"]
    parameter_names = {item["name"] for item in openapi["paths"]["/api/v1/port-scans"]["get"]["parameters"]}
    assert {"skip", "limit"} <= parameter_names


def test_port_scan_rate_limit_returns_429(client) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 0 open of 1 checked",
            checked_ports=[22],
            open_ports=[],
        )
    )

    for _ in range(_port_scan_rate_limit_capacity()):
        response = client.post(
            "/api/v1/port-scans/run",
            json={"ip": "192.168.56.23", "ports": [22]},
        )
        assert response.status_code == 201

    limited_response = client.post(
        "/api/v1/port-scans/run",
        json={"ip": "192.168.56.23", "ports": [22]},
    )

    client.app.dependency_overrides.clear()

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limit_exceeded"


def test_port_scan_rolls_back_when_repository_write_fails(client, monkeypatch) -> None:
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 1 checked",
            checked_ports=[22],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    async def broken_add(self, *, asset_id: int | None, ip: str, success: bool, message: str, checked_ports, open_ports):
        raise RuntimeError("port scan write failed")

    monkeypatch.setattr(PortScanRepository, "add", broken_add)

    with pytest.raises(RuntimeError, match="port scan write failed"):
        client.post(
            "/api/v1/port-scans/run",
            json={"ip": "192.168.56.24", "ports": [22]},
        )

    client.app.dependency_overrides.clear()
    monkeypatch.undo()

    list_response = client.get("/api/v1/port-scans")
    assert list_response.status_code == 200
    assert list_response.json() == []


def test_port_scanner_uses_settings() -> None:
    scanner = get_port_scanner(
        Settings(
            port_scan_connect_timeout_seconds=3,
            port_scan_default_ports="22,8443",
        )
    )

    assert scanner.timeout_seconds == 3
    assert scanner.default_ports == [22, 8443]
    assert scanner.max_concurrency == 50


def test_port_scanner_logs_unexpected_errors(monkeypatch, caplog) -> None:
    def raise_runtime_error(self, *, ip: str, port: int) -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(port_scan_client_module.PortScanner, "_is_port_open", raise_runtime_error)

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(
            port_scan_client_module.PortScanner(timeout_seconds=1, default_ports=[22]).scan(
                ip="192.168.56.25",
            )
        )

    assert result == PortScanExecution(
        success=False,
        message="Port scan failed",
        checked_ports=[22],
        open_ports=[],
    )
    assert "Unexpected port scan error" in caplog.text
    assert "RuntimeError" in caplog.text


def test_port_scanner_treats_refused_connections_as_closed_ports(monkeypatch) -> None:
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def fake_create_connection(address, timeout):
        if address[1] == 22:
            return FakeConnection()
        raise ConnectionRefusedError("closed")

    monkeypatch.setattr(port_scan_client_module.socket, "create_connection", fake_create_connection)

    result = asyncio.run(
        port_scan_client_module.PortScanner(timeout_seconds=1, default_ports=[22, 80]).scan(
            ip="192.168.56.26",
        )
    )

    assert result == PortScanExecution(
        success=True,
        message="Port scan completed: 1 open of 2 checked",
        checked_ports=[22, 80],
        open_ports=[PortScanPortState(port=22, is_open=True)],
    )
