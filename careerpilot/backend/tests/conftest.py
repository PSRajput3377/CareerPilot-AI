"""Shared pytest fixtures.

Each test runs against an isolated in-memory SQLite database with all tables
created fresh, so tests are hermetic and order-independent.
"""

from __future__ import annotations

import os

import pytest_asyncio

# Force a testing environment + in-memory DB before any app import reads config.
os.environ.setdefault("CAREERPILOT_ENV", "testing")
os.environ["CAREERPILOT_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import careerpilot.backend.models  # noqa: F401,E402  (register models on Base)
from careerpilot.backend.database.base import Base  # noqa: E402


@pytest_asyncio.fixture
async def engine():
    """A fresh in-memory engine per test (single shared connection)."""
    # StaticPool keeps the in-memory DB alive across sessions within one test.
    from sqlalchemy.pool import StaticPool

    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    """A session bound to the per-test engine."""
    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine) -> AsyncClient:
    """An httpx client wired to the FastAPI app, overriding get_db to use the
    per-test engine."""
    from careerpilot.backend.database.session import get_db
    from careerpilot.backend.main import create_app

    maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _override_get_db():
        async with maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app = create_app()
    # Avoid the lifespan's init_models touching a different engine.
    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
