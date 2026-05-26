"""In-memory crawl run tracking (per-target and crawl-all)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID


# Maximum time (seconds) a crawl can be "running" before it's considered stale.
# If a crawl entry is older than this, it's automatically expired on next check.
_STALE_THRESHOLD_SECONDS = 900  # 15 minutes


@dataclass
class RunningCrawl:
    target_id: str
    target_username: str
    platform: str
    started_at: str
    mode: str  # single | crawl_all | historical


_running: Dict[str, RunningCrawl] = {}
_crawl_all_active = False


def _is_stale(entry: RunningCrawl) -> bool:
    """Check if a running crawl entry has exceeded the stale threshold."""
    try:
        started = datetime.fromisoformat(entry.started_at)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        return elapsed > _STALE_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        # Can't parse timestamp — treat as stale
        return True


def _evict_stale() -> None:
    """Remove entries that have been running longer than the stale threshold."""
    stale_keys = [key for key, entry in _running.items() if _is_stale(entry)]
    for key in stale_keys:
        entry = _running.pop(key)
        # Import logger lazily to avoid circular imports at module level
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.warning(
            "Evicted stale crawl entry for @%s (started %s, exceeded %ds threshold)",
            entry.target_username,
            entry.started_at,
            _STALE_THRESHOLD_SECONDS,
        )


def register_running(
    target_id: UUID,
    target_username: str,
    platform: str,
    *,
    mode: str = "single",
) -> None:
    key = str(target_id)
    _running[key] = RunningCrawl(
        target_id=key,
        target_username=target_username,
        platform=platform,
        started_at=datetime.now(timezone.utc).isoformat(),
        mode=mode,
    )


def unregister_running(target_id: UUID) -> None:
    _running.pop(str(target_id), None)


def set_crawl_all_active(active: bool) -> None:
    global _crawl_all_active
    _crawl_all_active = active


def is_crawl_all_active() -> bool:
    return _crawl_all_active


def list_running() -> List[dict]:
    _evict_stale()
    return [
        {
            "target_id": r.target_id,
            "target_username": r.target_username,
            "platform": r.platform,
            "started_at": r.started_at,
            "mode": r.mode,
        }
        for r in _running.values()
    ]


def is_target_running(target_id: UUID) -> bool:
    key = str(target_id)
    if key not in _running:
        return False
    # Auto-evict if the entry is stale (prevents phantom "already running" blocks)
    if _is_stale(_running[key]):
        _evict_stale()
        return False
    return True
