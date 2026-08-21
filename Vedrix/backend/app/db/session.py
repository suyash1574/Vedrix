"""PostgreSQL-only async database session configuration."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlmodel import SQLModel

from app.core.config import settings

logger = logging.getLogger(__name__)

if not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
    raise ValueError("Vedrix requires a PostgreSQL asyncpg DATABASE_URL")

connect_args = {}
if settings.DB_SSL_MODE in {"require", "verify-full"}:
    # asyncpg accepts the boolean SSL switch through SQLAlchemy connect_args.
    # Certificate verification should be configured by the deployment platform
    # when verify-full is required.
    connect_args["ssl"] = True

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Verify PostgreSQL connectivity; schema changes are owned by Alembic."""
    if not await check_db_connection():
        raise RuntimeError("PostgreSQL is unavailable; refusing to start Vedrix")
    logger.info("PostgreSQL connectivity verified; schema is managed by Alembic")


async def get_session():
    """Yield a request-scoped async PostgreSQL session."""
    async with async_session() as session:
        yield session


async def check_db_connection() -> bool:
    """Verify that the configured PostgreSQL database accepts queries."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("PostgreSQL health check failed")
        return False
