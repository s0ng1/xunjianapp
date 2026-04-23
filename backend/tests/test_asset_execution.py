import asyncio

from app.db.session import get_session_factory
from app.features.assets.repository import AssetCredentialRepository
from app.features.linux_inspections.client import LinuxInspectionExecution
from app.features.port_scans.client import PortScanExecution
from app.features.port_scans.router import get_port_scanner
from app.features.port_scans.schemas import PortScanPortState
from app.features.ssh_test.client import SSHConnectionResult
from app.features.ssh_test.router import get_ssh_connector
from app.features.switch_inspections.client import SwitchInspectionResult
from app.features.switch_inspections.router import get_h3c_switch_inspector
from app.features.linux_inspections.router import get_linux_inspector


class FakeSSHConnector:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def test_connection(self, *, ip: str, username: str, password: str, port: int = 22) -> SSHConnectionResult:
        self.calls.append({"ip": ip, "username": username, "password": password, "port": port})
        return SSHConnectionResult(success=True, message="SSH connection succeeded")


class FakePortScanner:
    def __init__(self, execution: PortScanExecution) -> None:
        self.execution = execution

    async def scan(self, *, ip: str, ports: list[int] | None = None) -> PortScanExecution:
        return self.execution


class FakeLinuxInspector:
    def __init__(self, execution: LinuxInspectionExecution) -> None:
        self.execution = execution
        self.calls: list[dict] = []

    def inspect(
        self,
        *,
        ip: str,
        username: str,
        password: str,
        port: int = 22,
        collection_plan=None,
    ) -> LinuxInspectionExecution:
        self.calls.append({"ip": ip, "username": username, "password": password, "port": port})
        return self.execution


class FakeH3CSwitchInspector:
    def __init__(self, result: SwitchInspectionResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def inspect(self, *, ip: str, username: str, password: str, port: int = 22) -> SwitchInspectionResult:
        self.calls.append({"ip": ip, "username": username, "password": password, "port": port})
        return self.result


async def _load_encrypted_password(credential_id: int) -> str | None:
    async with get_session_factory()() as session:
        credential = await AssetCredentialRepository(session).get_by_id(credential_id)
        return credential.encrypted_password if credential is not None else None


def _create_linux_asset(client):
    response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.56.70",
            "type": "linux",
            "name": "prod-web-70",
            "username": "root",
            "credential_password": "linux-secret",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_switch_asset(client):
    response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.10.70",
            "type": "switch",
            "name": "core-sw-70",
            "username": "admin",
            "vendor": "h3c",
            "credential_password": "switch-secret",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_asset_credentials_are_encrypted_at_rest(client) -> None:
    asset = _create_linux_asset(client)

    encrypted_password = asyncio.run(_load_encrypted_password(asset["credential_id"]))

    assert encrypted_password is not None
    assert encrypted_password != "linux-secret"


def test_asset_ssh_test_uses_stored_credential(client) -> None:
    asset = _create_linux_asset(client)
    connector = FakeSSHConnector()
    client.app.dependency_overrides[get_ssh_connector] = lambda: connector

    response = client.post(f"/api/v1/assets/{asset['id']}/ssh-test")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "SSH connection succeeded"}
    assert connector.calls == [
        {
            "ip": "192.168.56.70",
            "username": "root",
            "password": "linux-secret",
            "port": 22,
        }
    ]


def test_asset_ssh_test_uses_rotated_stored_credential(client) -> None:
    asset = _create_linux_asset(client)
    update_response = client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"username": "secops", "credential_password": "linux-secret-rotated"},
    )
    assert update_response.status_code == 200

    connector = FakeSSHConnector()
    client.app.dependency_overrides[get_ssh_connector] = lambda: connector

    response = client.post(f"/api/v1/assets/{asset['id']}/ssh-test")

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert connector.calls == [
        {
            "ip": "192.168.56.70",
            "username": "secops",
            "password": "linux-secret-rotated",
            "port": 22,
        }
    ]


def test_asset_port_scan_saves_asset_reference(client) -> None:
    asset = _create_linux_asset(client)
    client.app.dependency_overrides[get_port_scanner] = lambda: FakePortScanner(
        PortScanExecution(
            success=True,
            message="Port scan completed: 1 open of 2 checked",
            checked_ports=[22, 443],
            open_ports=[PortScanPortState(port=22, is_open=True)],
        )
    )

    response = client.post(f"/api/v1/assets/{asset['id']}/port-scan", json={"ports": [22, 443]})

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_id"] == asset["id"]
    assert payload["ip"] == asset["ip"]


def test_asset_inspection_links_linux_result_back_to_asset(client) -> None:
    asset = _create_linux_asset(client)
    client.app.dependency_overrides[get_linux_inspector] = lambda: FakeLinuxInspector(
        LinuxInspectionExecution(success=True, message="Linux inspection completed")
    )

    response = client.post(f"/api/v1/assets/{asset['id']}/inspect")

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_id"] == asset["id"]
    assert payload["device_type"] == "linux"
    assert payload["inspection_id"] > 0

    inspections_response = client.get("/api/v1/linux-inspections")
    assert inspections_response.status_code == 200
    inspections = inspections_response.json()
    assert inspections[0]["asset_id"] == asset["id"]


def test_asset_inspection_passes_asset_port_to_linux_inspector(client) -> None:
    create_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.56.71",
            "type": "linux",
            "name": "prod-web-71",
            "port": 2222,
            "username": "root",
            "credential_password": "linux-secret",
        },
    )
    assert create_response.status_code == 201
    asset = create_response.json()

    inspector = FakeLinuxInspector(LinuxInspectionExecution(success=True, message="Linux inspection completed"))
    client.app.dependency_overrides[get_linux_inspector] = lambda: inspector

    response = client.post(f"/api/v1/assets/{asset['id']}/inspect")

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    assert inspector.calls == [
        {
            "ip": "192.168.56.71",
            "username": "root",
            "password": "linux-secret",
            "port": 2222,
        }
    ]


def test_asset_baseline_links_switch_result_back_to_asset(client) -> None:
    asset = _create_switch_asset(client)
    client.app.dependency_overrides[get_h3c_switch_inspector] = lambda: FakeH3CSwitchInspector(
        SwitchInspectionResult(
            success=True,
            message="H3C switch inspection completed",
            raw_config="undo telnet server enable\nstelnet server enable\nntp-service unicast-server 1.1.1.1\naaa",
        )
    )

    response = client.post(f"/api/v1/assets/{asset['id']}/baseline")

    client.app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_id"] == asset["id"]
    assert payload["device_type"] == "switch"
    assert payload["vendor"] == "H3C"

    inspections_response = client.get("/api/v1/switch-inspections")
    assert inspections_response.status_code == 200
    inspections = inspections_response.json()
    assert inspections[0]["asset_id"] == asset["id"]


def test_asset_inspection_requires_stored_credential(client) -> None:
    create_response = client.post(
        "/api/v1/assets",
        json={
            "ip": "192.168.56.71",
            "type": "linux",
            "name": "prod-web-71",
            "username": "root",
        },
    )
    assert create_response.status_code == 201
    asset_id = create_response.json()["id"]

    response = client.post(f"/api/v1/assets/{asset_id}/inspect")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "asset_missing_credential"
