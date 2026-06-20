"""Apply idempotent SQL migrations from backend/database/migrations/."""

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from utils.logger import get_logger

logger = get_logger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _split_sql_statements(sql: str) -> list[str]:
    """
    Split SQL on semicolons outside dollar-quoted blocks ($$ ... $$).
    Naive split(";") breaks PostgreSQL DO $$ ... END $$; blocks.
    """
    statements: list[str] = []
    current: list[str] = []
    in_dollar = False
    i = 0
    n = len(sql)
    while i < n:
        if i + 1 < n and sql[i : i + 2] == "$$":
            in_dollar = not in_dollar
            current.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue
        current.append(sql[i])
        i += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


async def apply_migration_file(engine: AsyncEngine, filename: str) -> None:
    """Execute one migration file (idempotent ALTER … IF NOT EXISTS)."""
    path = _MIGRATIONS_DIR / filename
    if not path.is_file():
        return
    sql = path.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql)
    async with engine.begin() as conn:
        logger.info("Applying migration: %s (%d statements)", filename, len(statements))
        for stmt in statements:
            await conn.execute(text(stmt))


async def run_pending_migrations(engine: AsyncEngine) -> None:
    """Apply incremental migrations safe on every startup."""
    await apply_migration_file(engine, "002_osint_evidence.sql")
    await apply_migration_file(engine, "003_target_crawl_checkpoints.sql")
    await apply_migration_file(engine, "004_website_safety_and_target_source.sql")
    await apply_migration_file(engine, "005_discovery_and_gender.sql")
    await apply_migration_file(engine, "006_evidence_verification.sql")
    await apply_migration_file(engine, "007_crawl_session_metadata.sql")
