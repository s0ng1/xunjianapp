import asyncio

import pytest

from app.core.exceptions import AppError
from app.core.config import get_settings
from app.db import session as session_module


class FakeConnection:
    def __init__(self) -> None:
        self.run_sync_calls = 0
        self.execute_calls = 0
        self.call_run_sync = False

    async def run_sync(self, fn):
        self.run_sync_calls += 1
        if self.call_run_sync:
            return fn(None)
        return None

    async def execute(self, statement) -> None:
        self.execute_calls += 1


class FakeBeginContext:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.enter_calls = 0

    async def __aenter__(self) -> FakeConnection:
        self.enter_calls += 1
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.begin_calls = 0
        self.connect_calls = 0

    def begin(self) -> FakeBeginContext:
        self.begin_calls += 1
        return FakeBeginContext(self.connection)

    def connect(self) -> FakeBeginContext:
        self.connect_calls += 1
        return FakeBeginContext(self.connection)


def test_init_database_skips_create_all_when_migrations_mode(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DB_SCHEMA_INIT_MODE", "migrations")
    session_module.get_settings.cache_clear()

    fake_engine = FakeEngine()
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)

    asyncio.run(session_module.init_database())

    assert fake_engine.begin_calls == 0
    assert fake_engine.connection.run_sync_calls == 0
    session_module.get_settings.cache_clear()


def test_init_database_runs_create_all_in_development(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DB_SCHEMA_INIT_MODE", raising=False)
    session_module.get_settings.cache_clear()

    fake_engine = FakeEngine()
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)

    asyncio.run(session_module.init_database())

    assert fake_engine.begin_calls == 1
    assert fake_engine.connection.run_sync_calls == 1
    session_module.get_settings.cache_clear()


def test_port_scan_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("PORT_SCAN_CONNECT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("PORT_SCAN_DEFAULT_PORTS", raising=False)
    monkeypatch.delenv("PORT_SCAN_RATE_LIMIT", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.port_scan_connect_timeout_seconds == 1
    assert settings.parsed_port_scan_default_ports == [22, 80, 443]
    assert settings.port_scan_rate_limit == "20/minute"

    get_settings.cache_clear()


def test_ensure_required_tables_accepts_ready_schema(monkeypatch) -> None:
    fake_engine = FakeEngine()
    fake_engine.connection.call_run_sync = True
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)
    monkeypatch.setattr(session_module, "_get_table_names", lambda _: set(session_module.REQUIRED_TABLES))

    asyncio.run(session_module.ensure_required_tables())

    assert fake_engine.connect_calls == 1
    assert fake_engine.connection.run_sync_calls == 1


def test_ensure_required_tables_rejects_missing_schema(monkeypatch) -> None:
    fake_engine = FakeEngine()
    fake_engine.connection.call_run_sync = True
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)
    monkeypatch.setattr(session_module, "_get_table_names", lambda _: {"assets", "asset_credentials"})

    with pytest.raises(AppError, match="missing tables"):
        asyncio.run(session_module.ensure_required_tables())


def test_ready_endpoint_checks_schema(client) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend"}
