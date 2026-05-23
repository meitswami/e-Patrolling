"""In-memory crawl run tracking (per-target and crawl-all)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID


@dataclass
class RunningCrawl:
    target_id: str
    target_username: str
    platform: str
    started_at: str
    mode: str  # single | crawl_all


_running: Dict[str, RunningCrawl] = {}
_crawl_all_active = False


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
    return str(target_id) in _running
