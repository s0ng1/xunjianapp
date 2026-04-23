from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.exceptions import AppError

from app.db.base import Base

REQUIRED_TABLES: tuple[str, ...] = (
    "assets",
    "asset_credentials",
    "linux_inspections",
    "switch_inspections",
    "port_scans",
    "baseline_check_results",
    "daily_focus_item_states",
    "scheduled_tasks",
)


def _engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite+aiosqlite"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {}


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        **_engine_options(settings.database_url),
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def ping_database() -> None:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(message="Database is not ready", status_code=503, code="database_unavailable") from exc


def _get_table_names(sync_connection) -> set[str]:
    inspector = sqlalchemy_inspect(sync_connection)
    return set(inspector.get_table_names())


async def ensure_required_tables(required_tables: tuple[str, ...] = REQUIRED_TABLES) -> None:
    try:
        async with get_engine().connect() as connection:
            existing_tables = await connection.run_sync(_get_table_names)
    except Exception as exc:
        raise AppError(
            message="Database schema is not ready",
            status_code=503,
            code="database_schema_unavailable",
        ) from exc

    missing_tables = [table for table in required_tables if table not in existing_tables]
    if missing_tables:
        raise AppError(
            message=f"Database schema is not ready, missing tables: {', '.join(missing_tables)}",
            status_code=503,
            code="database_schema_unavailable",
        )


async def init_database() -> None:
    settings = get_settings()
    if not settings.should_create_tables:
        return

    import app.db.models  # noqa: F401

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    engine = get_engine()
    await engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
