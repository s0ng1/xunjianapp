from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.features.assets.router import router as asset_router
from app.features.baseline.router import router as baseline_router
from app.features.daily_focus.router import router as daily_focus_router
from app.features.linux_inspections.router import router as linux_inspection_router
from app.features.port_scans.router import router as port_scan_router
from app.features.scheduled_tasks.router import router as scheduled_tasks_router
from app.features.ssh_test.router import router as ssh_test_router
from app.features.switch_inspections.router import router as switch_inspection_router

settings = get_settings()
api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(asset_router, prefix=settings.api_v1_prefix, tags=["assets"])
api_router.include_router(ssh_test_router, prefix=settings.api_v1_prefix, tags=["ssh"])
api_router.include_router(port_scan_router, prefix=settings.api_v1_prefix, tags=["port-scans"])
api_router.include_router(baseline_router, prefix=settings.api_v1_prefix, tags=["baseline-checks"])
api_router.include_router(daily_focus_router, prefix=settings.api_v1_prefix, tags=["daily-focus"])
api_router.include_router(linux_inspection_router, prefix=settings.api_v1_prefix, tags=["linux-inspections"])
api_router.include_router(switch_inspection_router, prefix=settings.api_v1_prefix, tags=["switch-inspections"])
api_router.include_router(scheduled_tasks_router, prefix=settings.api_v1_prefix, tags=["scheduled-tasks"])
