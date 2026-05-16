#!/usr/bin/env python3
"""
Run crawl pipeline for all active targets (CLI).

Usage (from repo root):
  python scripts/run_crawl.py
  python scripts/run_crawl.py --target-id <uuid>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from database import connection as db
from crawlers.pipeline import run_crawl_all_active, run_crawl_for_target
from utils.logger import get_logger

logger = get_logger(__name__)


async def main_async(target_id: str | None) -> int:
    await db.init_db()
    if db.async_session_factory is None:
        raise RuntimeError("Database not initialized")

    async with db.async_session_factory() as session:
        if target_id:
            summary = await run_crawl_for_target(session, UUID(target_id))
            logger.info("Result: %s", summary)
        else:
            summaries = await run_crawl_all_active(session)
            for s in summaries:
                logger.info("  %s", s)

    await db.close_db()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PATROL crawl runner")
    parser.add_argument("--target-id", help="Crawl single target UUID")
    args = parser.parse_args()
    try:
        return asyncio.run(main_async(args.target_id))
    except Exception as exc:
        logger.error("Crawl run failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
