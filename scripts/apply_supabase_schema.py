#!/usr/bin/env python3
"""
Apply PATROL schema to Supabase PostgreSQL.

Usage (from repo root):
  python scripts/apply_supabase_schema.py

Requires DATABASE_URL in .env (Supabase URI; postgresql+asyncpg://... is OK).

Alternative: Supabase Dashboard → SQL Editor → paste backend/database/supabase_migration.sql
Or Supabase MCP: apply_migration (after connecting .cursor/mcp.json)
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
load_dotenv(REPO / ".env")


def _database_url_direct() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def apply_with_psycopg() -> None:
    import psycopg  # noqa: PLC0415 — import after env load (avoid backend/queue shadowing stdlib)

    sql_path = BACKEND / "database" / "supabase_migration.sql"
    sql = sql_path.read_text(encoding="utf-8")
    conninfo = _database_url_direct()

    import ssl

    print(f"Applying schema from {sql_path.name} ...")
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    with psycopg.connect(conninfo, autocommit=True, sslcontext=ssl_ctx) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    print("Schema applied successfully.")


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "password@db.PROJECT_REF" in db_url:
        print("Set DATABASE_URL in .env to your Supabase connection string first.")
        return 1

    try:
        import psycopg  # noqa: F401
    except ImportError:
        print("Install: pip install 'psycopg[binary]'")
        print("Or paste backend/database/supabase_migration.sql into Supabase SQL Editor.")
        return 1

    try:
        apply_with_psycopg()
        return 0
    except Exception as exc:
        print(f"Failed: {exc}")
        print("\nIf tables already exist, this is expected. Use Supabase MCP list_tables to verify.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
