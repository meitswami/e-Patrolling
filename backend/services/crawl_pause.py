"""Cooperative pause/stop checks injected into crawler loops."""

from __future__ import annotations

from typing import Optional

from services.crawl_view_state import crawl_view_state


class CrawlPausedStop(Exception):
    """Raised when a view crawl is stopped by the user."""


async def check_crawl_pause(target_id: Optional[str]) -> None:
    """
    Block while paused; raise CrawlPausedStop when user stops the crawl.
    No-op when target_id is None (regular headless crawls).
    """
    if not target_id:
        return
    if crawl_view_state.should_stop(target_id):
        raise CrawlPausedStop(f"Crawl stopped for target {target_id}")
    await crawl_view_state.wait_if_paused(target_id)
    if crawl_view_state.should_stop(target_id):
        raise CrawlPausedStop(f"Crawl stopped for target {target_id}")
