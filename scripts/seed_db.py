#!/usr/bin/env python3
"""
Seed default admin user into Supabase/PostgreSQL.

Usage (from repo root):
  python scripts/seed_db.py

Requires DATABASE_URL in .env (Supabase connection string with +asyncpg).
Run scripts/apply_supabase_schema.py first if tables do not exist.
"""

import asyncio
import sys
from pathlib import Path

# Allow imports from backend/
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from auth.passwords import hash_password
from configs.settings import settings
from database import connection as db
from database.models import User, UserRole
from utils.logger import get_logger

logger = get_logger(__name__)


async def seed_admin() -> None:
    await db.init_db()
    if db.async_session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    email = settings.ADMIN_EMAIL.lower()
    async with db.async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            logger.info("Admin user already exists: %s", email)
            return

        user = User(
            email=email,
            name=settings.ADMIN_NAME,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        logger.info("Created admin user: %s (role=ADMIN)", email)

    await db.close_db()


def main() -> int:
    try:
        asyncio.run(seed_admin())
        return 0
    except Exception as exc:
        logger.error("Seed failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
