"""
Per-target crawl view state — pause / resume / stop during live view crawls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TargetCrawlViewState:
    target_id: str
    status: str = "idle"  # idle | running | paused | stopped
    view_mode: bool = False
    _pause_event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self._pause_event.set()

    def start(self, *, view_mode: bool = True) -> None:
        self.status = "running"
        self.view_mode = view_mode
        self._pause_event.set()

    def pause(self) -> None:
        if self.status == "running":
            self.status = "paused"
            self._pause_event.clear()

    def resume(self) -> None:
        if self.status == "paused":
            self.status = "running"
            self._pause_event.set()

    def stop(self) -> None:
        if self.status in ("running", "paused"):
            self.status = "stopped"
            self._pause_event.set()

    def reset(self) -> None:
        self.status = "idle"
        self.view_mode = False
        self._pause_event.set()

    async def wait_if_paused(self) -> None:
        await self._pause_event.wait()

    def should_stop(self) -> bool:
        return self.status == "stopped"

    def as_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "status": self.status,
            "view_mode": self.view_mode,
        }


class CrawlViewStateManager:
    """Runtime pause/resume for in-flight target crawls (view mode)."""

    def __init__(self) -> None:
        self._states: Dict[str, TargetCrawlViewState] = {}

    def _get(self, target_id: str) -> TargetCrawlViewState:
        key = str(target_id)
        if key not in self._states:
            self._states[key] = TargetCrawlViewState(target_id=key)
        return self._states[key]

    def start(self, target_id: str, *, view_mode: bool = True) -> None:
        self._get(target_id).start(view_mode=view_mode)

    def pause(self, target_id: str) -> bool:
        state = self._get(target_id)
        if state.status != "running":
            return False
        state.pause()
        return True

    def resume(self, target_id: str) -> bool:
        state = self._get(target_id)
        if state.status != "paused":
            return False
        state.resume()
        return True

    def stop(self, target_id: str) -> bool:
        state = self._get(target_id)
        if state.status not in ("running", "paused"):
            return False
        state.stop()
        return True

    def reset(self, target_id: str) -> None:
        self._get(target_id).reset()

    def get_status(self, target_id: str) -> dict:
        return self._get(target_id).as_dict()

    async def wait_if_paused(self, target_id: str) -> None:
        await self._get(target_id).wait_if_paused()

    def should_stop(self, target_id: str) -> bool:
        return self._get(target_id).should_stop()


crawl_view_state = CrawlViewStateManager()
