import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path) -> Generator[TestClient, None, None]:
    database_file = tmp_path / "assets-test.db"
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_allowed_origins = os.environ.get("ALLOWED_ORIGINS")
    previous_credential_encryption_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    previous_environment = os.environ.get("ENVIRONMENT")
    previous_db_schema_init_mode = os.environ.get("DB_SCHEMA_INIT_MODE")

    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_file.as_posix()}"
    os.environ["ALLOWED_ORIGINS"] = "http://testserver"
    os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "test-only-credential-key"
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DB_SCHEMA_INIT_MODE"] = "auto"

    from app.core.config import get_settings
    from app.core.rate_limit import limiter
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    storage = getattr(limiter, "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()

    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url

    if previous_allowed_origins is None:
        os.environ.pop("ALLOWED_ORIGINS", None)
    else:
        os.environ["ALLOWED_ORIGINS"] = previous_allowed_origins

    if previous_credential_encryption_key is None:
        os.environ.pop("CREDENTIAL_ENCRYPTION_KEY", None)
    else:
        os.environ["CREDENTIAL_ENCRYPTION_KEY"] = previous_credential_encryption_key

    if previous_environment is None:
        os.environ.pop("ENVIRONMENT", None)
    else:
        os.environ["ENVIRONMENT"] = previous_environment

    if previous_db_schema_init_mode is None:
        os.environ.pop("DB_SCHEMA_INIT_MODE", None)
    else:
        os.environ["DB_SCHEMA_INIT_MODE"] = previous_db_schema_init_mode
