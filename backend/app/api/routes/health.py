from fastapi import APIRouter

from app.db.session import ensure_required_tables, ping_database
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness_check() -> HealthResponse:
    await ping_database()
    await ensure_required_tables()
    return HealthResponse(status="ok", service="backend")
