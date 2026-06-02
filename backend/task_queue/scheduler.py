"""Periodic crawl scheduler (APScheduler) with overlap protection."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None
_crawl_all_lock = asyncio.Lock()

_scheduler_state: dict[str, Any] = {
    "last_run_at": None,
    "last_run_status": None,
    "last_run_message": None,
    "is_running": False,
    "skipped_overlapping": 0,
    "stop_requested": False,
    "last_export_at": None,
    "last_export_path": None,
}

_crawl_stop_requested = False


def get_scheduler_state() -> dict[str, Any]:
    """Snapshot for /crawlers/status."""
    state = dict(_scheduler_state)
    state["stop_requested"] = _crawl_stop_requested
    return state


def request_crawl_stop() -> None:
    """Signal in-flight crawl-all to stop after the current target."""
    global _crawl_stop_requested
    _crawl_stop_requested = True
    _scheduler_state["stop_requested"] = True


def is_crawl_stop_requested() -> bool:
    return _crawl_stop_requested


def clear_crawl_stop() -> None:
    global _crawl_stop_requested
    _crawl_stop_requested = False
    _scheduler_state["stop_requested"] = False


class CrawlInProgressError(Exception):
    """Raised when crawl-all is already running."""


@asynccontextmanager
async def crawl_all_lock() -> AsyncIterator[None]:
    """Serialize crawl-all across scheduler, API, and queue worker."""
    if _crawl_all_lock.locked():
        raise CrawlInProgressError("Crawl-all already in progress")
    async with _crawl_all_lock:
        _scheduler_state["is_running"] = True
        _scheduler_state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        try:
            yield
            _scheduler_state["last_run_status"] = "ok"
        except Exception as exc:
            _scheduler_state["last_run_status"] = "error"
            _scheduler_state["last_run_message"] = str(exc)
            raise
        finally:
            _scheduler_state["is_running"] = False


async def run_crawl_all_guarded() -> str:
    """
    Run crawl-all with a global lock so scheduler, API, and queue do not overlap.
    Returns a short status message.
    """
    if _crawl_all_lock.locked():
        _scheduler_state["skipped_overlapping"] = int(_scheduler_state.get("skipped_overlapping", 0)) + 1
        msg = "Crawl-all skipped — previous run still in progress"
        logger.warning(msg)
        return msg

    try:
        async with crawl_all_lock():
            from task_queue.consumer import execute_crawl_all

            results = await execute_crawl_all()
            ok = sum(1 for r in results if r.get("success"))
            _scheduler_state["last_run_message"] = f"Crawl-all complete: {ok}/{len(results)} targets"
            return _scheduler_state["last_run_message"]
    except CrawlInProgressError:
        _scheduler_state["skipped_overlapping"] = int(_scheduler_state.get("skipped_overlapping", 0)) + 1
        msg = "Crawl-all skipped — previous run still in progress"
        logger.warning(msg)
        return msg
    except Exception as exc:
        logger.exception("Crawl-all failed: %s", exc)
        raise


async def _scheduled_crawl_job() -> None:
    logger.info("Scheduler: triggering crawl-all")
    await run_crawl_all_guarded()


async def _weekly_evidence_export_job() -> None:
    """Write a CSV snapshot to exports/ for scheduled reporting."""
    from database.connection import async_session_factory
    from reports.weekly_export import run_weekly_evidence_export

    if not async_session_factory:
        return
    try:
        async with async_session_factory() as session:
            path = await run_weekly_evidence_export(session)
            _scheduler_state["last_export_at"] = datetime.now(timezone.utc).isoformat()
            _scheduler_state["last_export_path"] = str(path) if path else None
            logger.info("Weekly evidence export: %s", path)
    except Exception as exc:
        logger.exception("Weekly export failed: %s", exc)


async def _daily_discovery_job() -> None:
    """Run daily auto-discovery of female verified 10K+ accounts."""
    from database.connection import async_session_factory
    from services.discovery_crawler import run_discovery

    if not async_session_factory:
        return
    try:
        async with async_session_factory() as session:
            run = await run_discovery(session, triggered_by="scheduler")
            logger.info(
                "Daily discovery complete: %d profiles found (run %s)",
                run.total_found, run.id,
            )
    except Exception as exc:
        logger.exception("Daily discovery failed: %s", exc)


def start_scheduler() -> None:
    """Start periodic crawl-all when enabled and interval > 0."""
    global _scheduler
    if not settings.CRAWLER_SCHEDULER_ENABLED:
        logger.info("Crawl scheduler disabled (CRAWLER_SCHEDULER_ENABLED=false)")
        return
    if settings.CRAWL_INTERVAL_SECONDS <= 0:
        logger.info("Crawl scheduler disabled (CRAWL_INTERVAL_SECONDS=0)")
        return
    if _scheduler and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _scheduled_crawl_job,
        "interval",
        seconds=settings.CRAWL_INTERVAL_SECONDS,
        id="patrol_crawl_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if settings.WEEKLY_REPORT_EXPORT_ENABLED:
        _scheduler.add_job(
            _weekly_evidence_export_job,
            "cron",
            day_of_week=settings.WEEKLY_REPORT_DAY,
            hour=settings.WEEKLY_REPORT_HOUR,
            id="patrol_weekly_export",
            replace_existing=True,
            max_instances=1,
        )
    # Daily discovery: run at 2 AM every day
    _scheduler.add_job(
        _daily_discovery_job,
        "cron",
        hour=2,
        minute=0,
        id="shakti_daily_discovery",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info(
        "Crawl scheduler started — every %ss (max_instances=1, coalesce=True)",
        settings.CRAWL_INTERVAL_SECONDS,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
