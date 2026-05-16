"""Task definitions for the PATROL queue."""

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


async def schedule_crawl_target(target_id: UUID, *, run_inline_if_no_redis: bool = True) -> str:
    """
    Enqueue a crawl job. If Redis is off and run_inline_if_no_redis, runs in asyncio task.
    """
    payload = {"target_id": str(target_id)}
    if is_redis_available():
        await enqueue_task(QUEUE_KEY, _serialize(TaskType.CRAWL_TARGET, payload))
        return "queued"

    if run_inline_if_no_redis:
        import asyncio

        from task_queue.consumer import execute_crawl_target

        asyncio.create_task(execute_crawl_target(target_id))
        return "running_inline"

    raise RuntimeError("Redis disabled — cannot queue crawl; call pipeline directly")


async def schedule_crawl_all(*, run_inline_if_no_redis: bool = True) -> str:
    payload: dict[str, Any] = {}
    if is_redis_available():
        await enqueue_task(QUEUE_KEY, _serialize(TaskType.CRAWL_ALL, payload))
        return "queued"

    if run_inline_if_no_redis:
        import asyncio

        from task_queue.consumer import execute_crawl_all

        asyncio.create_task(execute_crawl_all())
        return "running_inline"

    raise RuntimeError("Redis disabled — cannot queue crawl_all")


async def parse_task(raw: str) -> tuple[TaskType, dict[str, Any]]:
    data = json.loads(raw)
    return TaskType(data["type"]), data.get("payload", {})
