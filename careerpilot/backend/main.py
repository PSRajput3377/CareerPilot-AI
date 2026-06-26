"""FastAPI application factory for CareerPilot AI."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from careerpilot.backend.api.errors import register_exception_handlers
from careerpilot.backend.api.v1 import api_router
from careerpilot.backend.config.settings import get_settings
from careerpilot.backend.core.logging import configure_logging, get_logger
from careerpilot.backend.database.session import dispose_engine, init_models

logger = get_logger("main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Bootstrap resources on startup, clean up on shutdown."""
    configure_logging()
    settings = get_settings()
    # In non-production, auto-create tables so the app runs out of the box.
    # Production relies on Alembic migrations.
    if not settings.is_production:
        await init_models()
    logger.info("CareerPilot AI started (env=%s)", settings.env)
    yield
    await dispose_engine()
    logger.info("CareerPilot AI shut down")


def create_app() -> FastAPI:
    """Application factory — returns a configured FastAPI instance."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered Job Search, Referral, Outreach and Follow-up Automation Platform",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    return app


app = create_app()
