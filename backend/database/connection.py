"""Async SQLAlchemy engine and session factory."""

import socket
import ssl
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine.url import make_url
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


def _resolve_database_url_ipv4(database_url: str) -> str:
    """
    Resolve DB hostname to IPv4 when DATABASE_FORCE_IPV4 is set.
    Fixes EC2 + Supabase: nc tries AAAA first → Network is unreachable (errno 101).
    """
    if not settings.DATABASE_FORCE_IPV4:
        return database_url
    try:
        parsed = make_url(database_url)
    except Exception:
        return database_url

    host = parsed.host
    if not host or host in ("localhost", "127.0.0.1"):
        return database_url
    try:
        socket.inet_aton(host)
        return database_url
    except OSError:
        pass

    try:
        infos = socket.getaddrinfo(
            host, None, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        ipv4 = infos[0][4][0]
        if ipv4 != host:
            logger.info(
                "Database host %s → IPv4 %s (DATABASE_FORCE_IPV4; no IPv6 route on VPC)",
                host,
                ipv4,
            )
            return parsed.set(host=ipv4).render_as_string(hide_password=False)
    except (socket.gaierror, IndexError, OSError) as exc:
        logger.warning("IPv4 resolution failed for %s: %s", host, exc)
    return database_url


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

    db_url = _resolve_database_url_ipv4(settings.DATABASE_URL)
    engine = create_async_engine(
        db_url,
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
