import logging

from app.core.config import Settings
from app.core.config import get_settings
from app.features.ssh_test import client as ssh_client_module
from app.features.ssh_test.client import SSHConnectionResult
from app.features.ssh_test.router import get_ssh_connector


class FakeSSHConnector:
    def __init__(self, result: SSHConnectionResult) -> None:
        self.result = result

    def test_connection(self, *, ip: str, username: str, password: str) -> SSHConnectionResult:
        return self.result


def _ssh_rate_limit_capacity() -> int:
    return int(get_settings().ssh_test_rate_limit.split("/", maxsplit=1)[0])


def test_ssh_connection_success(client) -> None:
    client.app.dependency_overrides[get_ssh_connector] = lambda: FakeSSHConnector(
        SSHConnectionResult(success=True, message="SSH connection succeeded")
    )

    response = client.post(
        "/api/v1/ssh/test",
        json={
            "ip": "192.168.1.20",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "SSH connection succeeded",
    }


def test_ssh_connection_failure(client) -> None:
    client.app.dependency_overrides[get_ssh_connector] = lambda: FakeSSHConnector(
        SSHConnectionResult(success=False, message="SSH authentication failed")
    )

    response = client.post(
        "/api/v1/ssh/test",
        json={
            "ip": "192.168.1.21",
            "username": "admin",
            "password": "wrong-password",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "message": "SSH authentication failed",
    }


def test_ssh_password_is_not_logged(client, caplog) -> None:
    secret = "UltraSecretPassword123!"
    client.app.dependency_overrides[get_ssh_connector] = lambda: FakeSSHConnector(
        SSHConnectionResult(success=False, message="SSH connection failed")
    )

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/ssh/test",
            json={
                "ip": "192.168.1.22",
                "username": "tester",
                "password": secret,
            },
        )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert secret not in caplog.text


def test_ssh_validation_error_for_blank_username(client) -> None:
    response = client.post(
        "/api/v1/ssh/test",
        json={
            "ip": "192.168.1.23",
            "username": "   ",
            "password": "secret",
        },
    )

    assert response.status_code == 422


def test_ssh_request_trims_ip_whitespace(client) -> None:
    client.app.dependency_overrides[get_ssh_connector] = lambda: FakeSSHConnector(
        SSHConnectionResult(success=True, message="SSH connection succeeded")
    )

    response = client.post(
        "/api/v1/ssh/test",
        json={
            "ip": " 192.168.1.23 ",
            "username": "root",
            "password": "secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_openapi_exposes_ssh_test_endpoint(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert "/api/v1/ssh/test" in openapi["paths"]


def test_ssh_test_rate_limit_returns_429(client) -> None:
    client.app.dependency_overrides[get_ssh_connector] = lambda: FakeSSHConnector(
        SSHConnectionResult(success=True, message="SSH connection succeeded")
    )

    for _ in range(_ssh_rate_limit_capacity()):
        response = client.post(
            "/api/v1/ssh/test",
            json={
                "ip": "192.168.1.24",
                "username": "root",
                "password": "super-secret",
            },
        )
        assert response.status_code == 200

    limited_response = client.post(
        "/api/v1/ssh/test",
        json={
            "ip": "192.168.1.24",
            "username": "root",
            "password": "super-secret",
        },
    )

    client.app.dependency_overrides.clear()

    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limit_exceeded"


def test_ssh_connector_uses_timeout_from_settings() -> None:
    connector = get_ssh_connector(Settings(ssh_connection_timeout_seconds=17))

    assert connector.timeout_seconds == 17


def test_ssh_connector_logs_unexpected_errors(monkeypatch, caplog) -> None:
    secret = "StillNotLogged123!"

    def raise_runtime_error(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ssh_client_module, "ConnectHandler", raise_runtime_error)

    with caplog.at_level(logging.ERROR):
        result = ssh_client_module.SSHConnector(timeout_seconds=9).test_connection(
            ip="192.168.1.25",
            username="root",
            password=secret,
        )

    assert result == SSHConnectionResult(success=False, message="SSH connection failed")
    assert "Unexpected SSH connection error" in caplog.text
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text
