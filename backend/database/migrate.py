"""Apply idempotent SQL migrations from backend/database/migrations/."""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from utils.logger import get_logger

logger = get_logger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def apply_migration_file(engine: AsyncEngine, filename: str) -> None:
    """Execute one migration file (idempotent ALTER … IF NOT EXISTS)."""
    path = _MIGRATIONS_DIR / filename
    if not path.is_file():
        return
    sql = path.read_text(encoding="utf-8")
    async with engine.begin() as conn:
        logger.info("Applying migration: %s", filename)
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))


async def run_pending_migrations(engine: AsyncEngine) -> None:
    """Apply incremental migrations safe on every startup."""
    await apply_migration_file(engine, "002_osint_evidence.sql")
    await apply_migration_file(engine, "003_target_crawl_checkpoints.sql")
    await apply_migration_file(engine, "004_website_safety_and_target_source.sql")
