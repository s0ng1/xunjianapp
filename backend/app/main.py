from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler, unhandled_exception_handler
from app.core.logging import RequestIDMiddleware, configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.session import dispose_engine, get_session_factory, init_database
from app.features.scheduled_tasks.scheduler import SchedulerManager

configure_logging()
scheduler_manager: SchedulerManager | None = None


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        global scheduler_manager
        await init_database()
        scheduler_manager = SchedulerManager(get_session_factory())
        await scheduler_manager.start()
        yield
        if scheduler_manager is not None:
            await scheduler_manager.shutdown()
        await dispose_engine()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Security inspection platform backend APIs.",
        lifespan=lifespan,
    )
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(api_router)
    return app


app = create_app()
