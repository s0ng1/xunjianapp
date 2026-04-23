import json
import os
import urllib.error
import urllib.request
import uuid
from collections.abc import Generator
from contextlib import closing

import psycopg
import pytest
from sqlalchemy.engine import make_url


def _integration_enabled() -> bool:
    return os.environ.get("RUN_POSTGRES_INTEGRATION", "").lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="module")
def postgres_integration_settings() -> Generator[dict[str, str], None, None]:
    if not _integration_enabled():
        pytest.skip("set RUN_POSTGRES_INTEGRATION=1 to run PostgreSQL integration tests")

    base_url = os.environ.get("POSTGRES_INTEGRATION_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        pytest.fail("DATABASE_URL must be set for PostgreSQL integration tests")

    parsed = make_url(database_url)
    if not parsed.drivername.startswith("postgresql"):
        pytest.fail(f"DATABASE_URL must target PostgreSQL, got {parsed.drivername}")

    yield {
        "base_url": base_url,
        "database_url": database_url,
    }


def _request(base_url: str, method: str, path: str, payload: dict | None = None) -> tuple[int, object | None]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(f"{base_url}{path}", data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read()
            if not body:
                return response.status, None
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {path} returned {exc.code}: {error_body}") from exc


def _connect_postgres(database_url: str) -> psycopg.Connection:
    parsed = make_url(database_url)
    return psycopg.connect(
        host=parsed.host,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        dbname=parsed.database,
    )


@pytest.mark.postgres_integration
def test_ready_endpoint_passes_with_postgres(postgres_integration_settings: dict[str, str]) -> None:
    status, payload = _request(postgres_integration_settings["base_url"], "GET", "/ready")

    assert status == 200
    assert payload == {"status": "ok", "service": "backend"}


@pytest.mark.postgres_integration
def test_asset_lifecycle_persists_to_postgres(postgres_integration_settings: dict[str, str]) -> None:
    asset_ip = f"198.51.100.{uuid.uuid4().int % 200 + 1}"
    asset_name = f"pg-integration-{uuid.uuid4().hex[:8]}"
    base_url = postgres_integration_settings["base_url"]
    asset_id: int | None = None
    deleted = False

    try:
        status, created = _request(
            base_url,
            "POST",
            "/api/v1/assets",
            {
                "ip": asset_ip,
                "type": "linux",
                "name": asset_name,
            },
        )

        assert status == 201
        assert isinstance(created, dict)
        assert created["ip"] == asset_ip
        assert created["name"] == asset_name
        asset_id = created["id"]

        with closing(_connect_postgres(postgres_integration_settings["database_url"])) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT ip, asset_type, name, connection_type, port, is_enabled
                    FROM assets
                    WHERE id = %s
                    """,
                    (asset_id,),
                )
                stored_row = cursor.fetchone()

        assert stored_row == (asset_ip, "linux", asset_name, "ssh", 22, True)

        status, listed_assets = _request(base_url, "GET", "/api/v1/assets")

        assert status == 200
        assert isinstance(listed_assets, list)
        assert any(item["id"] == asset_id for item in listed_assets)

        status, _ = _request(base_url, "DELETE", f"/api/v1/assets/{asset_id}")

        assert status == 204
        deleted = True

        with closing(_connect_postgres(postgres_integration_settings["database_url"])) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM assets WHERE id = %s", (asset_id,))
                deleted_row = cursor.fetchone()

        assert deleted_row is None
    finally:
        if asset_id is not None and not deleted:
            try:
                _request(base_url, "DELETE", f"/api/v1/assets/{asset_id}")
            except AssertionError:
                pass
