"""Async SQLAlchemy engine and session factory."""

import ssl
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def verify_db_connection() -> None:
    """Open one connection at startup; raises if the host is unreachable."""
    if engine is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db() -> None:
    """Create async engine and session factory."""
    global engine, async_session_factory

    connect_args: dict = {}
    if settings.DATABASE_SSL or settings.uses_supabase:
        if settings.DATABASE_SSL_VERIFY:
            connect_args["ssl"] = ssl.create_default_context()
        else:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx

    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=settings.DEBUG,
        connect_args=connect_args,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Database engine initialized")


async def close_db() -> None:
    """Dispose connection pool on shutdown."""
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        logger.info("Database engine disposed")
    engine = None
    async_session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
