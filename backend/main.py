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

    # Initialize Redis connection
    from queue.producer import init_redis, close_redis
    await init_redis()
    logger.info("✅ Redis connection initialized")

    # Pre-load AI models (lazy, only if enabled)
    if settings.PRELOAD_AI_MODELS:
        from ai.model_loader import preload_models
        await preload_models()
        logger.info("✅ AI models pre-loaded")

    # Initialize WebSocket manager
    from websocket.manager import ws_manager
    logger.info("✅ WebSocket manager ready")

    logger.info("✅ PATROL Backend is ready — monitoring begins")

    yield  # Application runs here

    # Graceful shutdown
    logger.info("🛑 PATROL Backend shutting down...")
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
    version="1.0.0-MVP",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── Middleware ───────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {
        "status": "healthy",
        "service": "PATROL API",
        "version": "1.0.0-MVP",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """API root — redirects to docs."""
    return JSONResponse(
        content={
            "message": "PATROL API — Predictive Abuse Tracking & Regional Observation Layer",
            "docs": "/docs",
            "health": "/health",
            "version": "1.0.0-MVP",
        }
    )


# ── Register Routers ─────────────────────────────────────────
# NOTE: Routes are imported here to avoid circular imports.
# Each module lazily imports DB/service dependencies.

def register_routers():
    """Register all API route modules."""
    from api.routes.auth import router as auth_router
    from api.routes.targets import router as targets_router
    from api.routes.evidence import router as evidence_router
    from api.routes.analytics import router as analytics_router
    from api.routes.reports import router as reports_router
    from api.routes.search import router as search_router
    from api.routes.regions import router as regions_router
    from api.routes.offenders import router as offenders_router
    from api.routes.ws import router as ws_router

    PREFIX = "/api/v1"

    app.include_router(auth_router,      prefix=f"{PREFIX}/auth",      tags=["Authentication"])
    app.include_router(targets_router,   prefix=f"{PREFIX}/targets",   tags=["Target Accounts"])
    app.include_router(evidence_router,  prefix=f"{PREFIX}/evidence",  tags=["Evidence"])
    app.include_router(analytics_router, prefix=f"{PREFIX}/analytics", tags=["Analytics"])
    app.include_router(reports_router,   prefix=f"{PREFIX}/reports",   tags=["Reports"])
    app.include_router(search_router,    prefix=f"{PREFIX}/search",    tags=["Search"])
    app.include_router(regions_router,   prefix=f"{PREFIX}/regions",   tags=["Region Intelligence"])
    app.include_router(offenders_router, prefix=f"{PREFIX}/offenders", tags=["Repeat Offenders"])
    app.include_router(ws_router,        prefix="/ws",                  tags=["WebSocket"])


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