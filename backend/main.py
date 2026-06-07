"""
PATROL Backend — FastAPI Application Entry Point
=================================================
Mounts all routers, configures middleware, initializes services.

Architecture:
  - Async-first (asyncpg, asyncio, async Playwright)
  - WebSocket support for real-time dashboard
  - JWT authentication on all protected routes
  - Structured logging (JSON format in production)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from configs.settings import settings
from configs.logging_config import setup_logging
from utils.logger import get_logger

logger = get_logger(__name__)


# ── Lifespan: startup / shutdown ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    Handles startup initialization and graceful shutdown.
    """
    logger.info("🚀 PATROL Backend starting up...")

    # Initialize database connection pool
    from database.connection import init_db, close_db
    await init_db()
    logger.info("✅ Database connection pool initialized")

    from database.connection import (
        async_session_factory,
        engine as db_engine,
        verify_db_connection,
    )
    from database.models import SystemSetting
    from services import system_settings as sys_settings

    db_ok = False
    try:
        await verify_db_connection()
        db_ok = True
        logger.info("✅ Database reachable (Supabase)")
    except OSError as exc:
        logger.error(
            "❌ Database host unreachable (%s). "
            "EC2 needs outbound internet (IGW/NAT) and port 5432 open. "
            "Use repo-root .env or backend/.env with DATABASE_URL; "
            "On EC2 use Session pooler host (aws-*-REGION.pooler.supabase.com), not db.<project>.supabase.co (IPv6-only).",
            exc,
        )
    except Exception as exc:
        logger.error("❌ Database connection failed: %s", exc)

    if db_ok and async_session_factory and db_engine:
        try:
            from database.migrate import run_pending_migrations

            await run_pending_migrations(db_engine)
            from database.models import TargetCrawlCheckpoint

            async with db_engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: SystemSetting.__table__.create(sync_conn, checkfirst=True)
                )
                await conn.run_sync(
                    lambda sync_conn: TargetCrawlCheckpoint.__table__.create(sync_conn, checkfirst=True)
                )
            async with async_session_factory() as session:
                await sys_settings.load_cache(session)
                await sys_settings.upsert_crawler_settings(
                    session,
                    crawler_demo_mode=False,
                )
                await session.commit()
            logger.info("✅ System settings loaded from database")
        except Exception as exc:
            logger.warning("System settings bootstrap skipped: %s", exc)

    # Initialize Redis (optional — not required for auth/API MVP)
    from task_queue.producer import init_redis, close_redis, is_redis_available

    if await init_redis():
        logger.info("✅ Redis connection initialized")
    else:
        logger.info("ℹ️ Redis skipped — auth and REST API still available")

    # Pre-load AI models (lazy, only if enabled)
    if settings.PRELOAD_AI_MODELS:
        from ai.model_loader import preload_models
        await preload_models()
        logger.info("✅ AI models pre-loaded")

    # Initialize WebSocket manager
    from websocket.manager import ws_manager
    logger.info("✅ WebSocket manager ready")

    from task_queue.consumer import start_background_consumer
    from task_queue.scheduler import start_scheduler

    start_background_consumer()
    if settings.CRAWLER_SCHEDULER_ENABLED:
        start_scheduler()
        logger.info("✅ Crawl scheduler started")

    logger.info("✅ PATROL Backend is ready — monitoring begins")

    yield  # Application runs here

    # Graceful shutdown
    logger.info("🛑 PATROL Backend shutting down...")
    from task_queue.consumer import stop_background_consumer
    from task_queue.scheduler import stop_scheduler

    stop_scheduler()
    stop_background_consumer()
    await close_db()
    await close_redis()
    logger.info("✅ Cleanup complete")


# ── FastAPI App ─────────────────────────────────────────────

app = FastAPI(
    title="PATROL API",
    description="""
    ## Predictive Abuse Tracking & Regional Observation Layer
    
    AI-Powered Social Media Harassment Intelligence System
    
    ### For:
    - 🚔 Cyber Cells & Law Enforcement
    - 🛡️ Women Safety Organizations  
    - 🔍 OSINT Teams
    
    ### Capabilities:
    - Multi-platform social media monitoring
    - Hindi + Hinglish + English abuse detection
    - Real-time evidence collection
    - Regional threat intelligence
    - Repeat offender tracking
    """,
    version="1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ───────────────────────────────────────────────

_cors_regex = settings.CORS_ORIGIN_REGEX if settings.ENVIRONMENT == "production" else None
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
logger.info(
    "CORS: origins=%s regex=%s",
    settings.effective_cors_origins,
    _cors_regex or "(disabled)",
)


# ── Static Files (evidence screenshots) ─────────────────────

app.mount(
    "/storage",
    StaticFiles(directory=str(settings.EVIDENCE_STORAGE_PATH.parent)),
    name="storage",
)


# ── Health Check ─────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """System health check for Docker and load balancers."""
    from database.connection import engine as db_engine, verify_db_connection
    from task_queue.producer import is_redis_available

    db_status = "not_initialized"
    if db_engine is not None:
        try:
            await verify_db_connection()
            db_status = "connected"
        except Exception as exc:
            db_status = f"error: {exc}"

    from database.connection import database_host_hint

    overall = "healthy" if db_status == "connected" else "degraded"
    payload = {
        "status": overall,
        "service": "PATROL API",
        "version": "1.0",
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "database_host": database_host_hint(),
        "redis": "connected" if is_redis_available() else "disabled",
        "cors_origins": settings.effective_cors_origins,
        "cors_origin_regex": _cors_regex,
    }
    if overall != "healthy":
        payload["fix"] = (
            "EC2: set DATABASE_URL to Session pooler (postgresql+asyncpg://postgres.PROJECT_REF:pass@"
            "aws-*-REGION.pooler.supabase.com:5432/postgres). "
            "Not db.PROJECT.supabase.co (IPv6)."
        )
    return payload


@app.get("/", tags=["System"])
async def root():
    """API root — redirects to docs."""
    return JSONResponse(
        content={
            "message": "PATROL API — Predictive Abuse Tracking & Regional Observation Layer",
            "docs": "/docs",
            "health": "/health",
            "version": "1.0",
        }
    )


# ── Register Routers ─────────────────────────────────────────
# NOTE: Routes are imported here to avoid circular imports.
# Each module lazily imports DB/service dependencies.

def register_routers() -> None:
    """Register API routers as modules are implemented (see docs/task_tracker.md)."""
    PREFIX = "/api/v1"

    from api.routes.auth import router as auth_router
    from api.routes.targets import router as targets_router
    from api.routes.evidence import router as evidence_router
    from api.routes.analytics import router as analytics_router
    from api.routes.crawlers import router as crawlers_router
    from api.routes.offenders import router as offenders_router
    from api.routes.ai import router as ai_router
    from api.routes.regions import router as regions_router
    from api.routes.reports import router as reports_router
    from api.routes.settings import router as settings_router
    from api.routes.public import router as public_router
    from api.routes.website_requests import router as website_requests_router
    from api.routes.websocket import router as ws_router
    from api.routes.system_metrics import router as system_metrics_router
    from api.routes.lexicon import router as lexicon_router
    from api.routes.discovery import router as discovery_router
    from api.routes.target_import import router as target_import_router
    from api.routes.profile_preview import router as profile_preview_router

    app.include_router(public_router, prefix=f"{PREFIX}/public", tags=["Public Website"])
    app.include_router(
        profile_preview_router,
        prefix=f"{PREFIX}/public",
        tags=["Public Website"],
    )
    app.include_router(
        website_requests_router,
        prefix=f"{PREFIX}/website-requests",
        tags=["Website Intake"],
    )
    app.include_router(auth_router, prefix=f"{PREFIX}/auth", tags=["Authentication"])
    app.include_router(targets_router, prefix=f"{PREFIX}/targets", tags=["Target Accounts"])
    app.include_router(evidence_router, prefix=f"{PREFIX}/evidence", tags=["Evidence"])
    app.include_router(analytics_router, prefix=f"{PREFIX}/analytics", tags=["Analytics"])
    app.include_router(crawlers_router, prefix=f"{PREFIX}/crawlers", tags=["Crawlers"])
    app.include_router(offenders_router, prefix=f"{PREFIX}/offenders", tags=["Offenders"])
    app.include_router(reports_router, prefix=f"{PREFIX}/reports", tags=["Reports"])
    app.include_router(regions_router, prefix=f"{PREFIX}/regions", tags=["Regions"])
    app.include_router(ai_router, prefix=f"{PREFIX}/ai", tags=["AI"])
    app.include_router(settings_router, prefix=f"{PREFIX}/settings", tags=["Settings"])
    app.include_router(system_metrics_router, prefix=f"{PREFIX}/metrics", tags=["Metrics"])
    app.include_router(lexicon_router, prefix=f"{PREFIX}/lexicon", tags=["Abuse Dictionary"])
    app.include_router(discovery_router, prefix=f"{PREFIX}/discovery", tags=["Auto-Discovery"])
    app.include_router(target_import_router, prefix=f"{PREFIX}/targets/import", tags=["Target Import"])
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
    logger.info("Registered API routers under %s", PREFIX)


register_routers()
setup_logging()


# ── Exception Handlers ───────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Resource not found", "path": str(request.url)},
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Check logs for details."},
    )


# ── Dev server entry point ───────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        workers=1,  # Single worker for dev; use gunicorn in prod
    )