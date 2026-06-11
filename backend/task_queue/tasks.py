"""Task definitions for the PATROL queue."""

import asyncio
import json
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from task_queue.producer import enqueue_task, is_redis_available
from utils.logger import get_logger

logger = get_logger(__name__)

QUEUE_KEY = "patrol:tasks"


class TaskType(str, Enum):
    CRAWL_TARGET = "crawl_target"
    CRAWL_ALL = "crawl_all"


def _serialize(task_type: TaskType, payload: dict[str, Any]) -> str:
    return json.dumps({"type": task_type.value, "payload": payload})


async def _safe_execute_crawl_target(target_id: UUID) -> None:
    """
    Wrapper around execute_crawl_target that catches all exceptions.
    Prevents fire-and-forget tasks from silently leaking resources (browser
    instances, DB connections) on unhandled errors.
    """
    from task_queue.consumer import execute_crawl_target

    try:
        await asyncio.wait_for(
            execute_crawl_target(target_id),
            timeout=600,  # 10 minute hard timeout per target crawl
        )
    except asyncio.TimeoutError:
        logger.error(
            "Crawl task for target %s timed out after 600s — forcing cleanup",
            target_id,
        )
        # Ensure the target is unregistered from crawl_state
        from crawlers.crawl_state import unregister_running
        unregister_running(target_id)
    except Exception as exc:
        logger.error(
            "Inline crawl task failed for target %s: %s", target_id, exc, exc_info=True
        )
        from crawlers.crawl_state import unregister_running
        unregister_running(target_id)


async def _safe_execute_crawl_all() -> None:
    """
    Wrapper around execute_crawl_all that catches all exceptions.
    Prevents fire-and-forget tasks from silently dying and leaking resources.
    """
    from task_queue.consumer import execute_crawl_all

    try:
        await asyncio.wait_for(
            execute_crawl_all(),
            timeout=1800,  # 30 minute hard timeout for crawl-all
        )
    except asyncio.TimeoutError:
        logger.error("Crawl-all task timed out after 1800s — forcing cleanup")
    except Exception as exc:
        logger.error("Inline crawl-all task failed: %s", exc, exc_info=True)


async def _safe_execute_view_crawl(target_id: UUID, *, historical: bool = False) -> None:
    """Background view crawl with visible browser."""
    from database import connection as db
    from crawlers.pipeline import run_crawl_for_target
    from crawlers.crawl_state import unregister_running

    try:
        if db.async_session_factory is None:
            await db.init_db()
        async with db.async_session_factory() as session:
            await asyncio.wait_for(
                run_crawl_for_target(
                    session,
                    target_id,
                    historical=historical,
                    view_mode=True,
                ),
                timeout=900 if historical else 600,
            )
    except asyncio.TimeoutError:
        logger.error("View crawl timed out for target %s", target_id)
        unregister_running(target_id)
    except Exception as exc:
        logger.error("View crawl failed for target %s: %s", target_id, exc, exc_info=True)
        unregister_running(target_id)


async def schedule_view_crawl_target(
    target_id: UUID,
    *,
    historical: bool = False,
) -> str:
    """Start view crawl in background (visible browser + live feed)."""
    asyncio.create_task(
        _safe_execute_view_crawl(target_id, historical=historical),
        name=f"view_crawl_{target_id}",
    )
    return "running_inline"


async def schedule_crawl_target(target_id: UUID, *, run_inline_if_no_redis: bool = True) -> str:
    """
    Enqueue a crawl job. If Redis is off and run_inline_if_no_redis, runs in asyncio task.
    """
    payload = {"target_id": str(target_id)}
    if is_redis_available():
        await enqueue_task(QUEUE_KEY, _serialize(TaskType.CRAWL_TARGET, payload))
        return "queued"

    if run_inline_if_no_redis:
        asyncio.create_task(
            _safe_execute_crawl_target(target_id),
            name=f"crawl_target_{target_id}",
        )
        return "running_inline"

    raise RuntimeError("Redis disabled — cannot queue crawl; call pipeline directly")


async def schedule_crawl_all(*, run_inline_if_no_redis: bool = True) -> str:
    payload: dict[str, Any] = {}
    if is_redis_available():
        await enqueue_task(QUEUE_KEY, _serialize(TaskType.CRAWL_ALL, payload))
        return "queued"

    if run_inline_if_no_redis:
        asyncio.create_task(
            _safe_execute_crawl_all(),
            name="crawl_all",
        )
        return "running_inline"

    raise RuntimeError("Redis disabled — cannot queue crawl_all")


async def parse_task(raw: str) -> tuple[TaskType, dict[str, Any]]:
    data = json.loads(raw)
    return TaskType(data["type"]), data.get("payload", {})
