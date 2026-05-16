"""Task queue consumer — Redis BRPOP loop or direct execution."""

import asyncio
from uuid import UUID

from database import connection as db
from task_queue.producer import get_redis, is_redis_available
from task_queue.tasks import QUEUE_KEY, TaskType, parse_task
from utils.logger import get_logger

logger = get_logger(__name__)

_consumer_task: asyncio.Task | None = None


async def execute_crawl_target(target_id: UUID) -> dict:
    from crawlers.pipeline import run_crawl_for_target

    if db.async_session_factory is None:
        await db.init_db()
    async with db.async_session_factory() as session:
        return await run_crawl_for_target(session, target_id)


async def execute_crawl_all() -> list:
    from crawlers.pipeline import run_crawl_all_active

    if db.async_session_factory is None:
        await db.init_db()
    async with db.async_session_factory() as session:
        return await run_crawl_all_active(session)


async def _handle_task(task_type: TaskType, payload: dict) -> None:
    if task_type == TaskType.CRAWL_TARGET:
        target_id = UUID(payload["target_id"])
        result = await execute_crawl_target(target_id)
        logger.info("Crawl task done: %s", result)
    elif task_type == TaskType.CRAWL_ALL:
        from task_queue.scheduler import run_crawl_all_guarded

        msg = await run_crawl_all_guarded()
        logger.info("Crawl-all done: %s", msg)
    else:
        logger.warning("Unknown task type: %s", task_type)


async def _consumer_loop() -> None:
    redis = get_redis()
    logger.info("Queue consumer started on %s", QUEUE_KEY)
    while True:
        try:
            item = await redis.brpop(QUEUE_KEY, timeout=5)
            if not item:
                continue
            _, raw = item
            task_type, payload = await parse_task(raw)
            await _handle_task(task_type, payload)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Consumer error: %s", exc)
            await asyncio.sleep(2)


def start_background_consumer() -> None:
    """Start Redis consumer if available."""
    global _consumer_task
    if not is_redis_available():
        logger.info("Queue consumer not started (Redis disabled)")
        return
    if _consumer_task and not _consumer_task.done():
        return
    _consumer_task = asyncio.create_task(_consumer_loop())
    logger.info("Background queue consumer scheduled")


def stop_background_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
    _consumer_task = None
