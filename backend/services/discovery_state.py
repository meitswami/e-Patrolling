"""
Discovery State Manager
========================
Singleton module managing discovery run state: play/pause/stop signaling,
progress tracking, and live log streaming via an in-memory deque.
"""

import asyncio
import collections
from datetime import datetime, timezone
from typing import Optional


class DiscoveryState:
    """Manages the runtime state of a discovery run."""

    def __init__(self) -> None:
        self.status: str = "idle"
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()  # Not paused by default
        self.max_count: int = 25
        self.progress_count: int = 0
        self.current_run_id: Optional[str] = None
        self._logs: collections.deque = collections.deque(maxlen=500)
        self._log_index: int = 0

    def start(self, max_count: int, run_id: str) -> None:
        """Initialize state for a new discovery run."""
        self.status = "running"
        self.max_count = max_count
        self.progress_count = 0
        self.current_run_id = run_id
        self._pause_event.set()
        self._logs.clear()
        self._log_index = 0
        self.emit_log(f"Discovery started (max: {max_count} profiles)")

    def pause(self) -> None:
        """Pause the running discovery."""
        if self.status == "running":
            self.status = "paused"
            self._pause_event.clear()
            self.emit_log("Discovery paused", level="warning")

    def resume(self) -> None:
        """Resume a paused discovery."""
        if self.status == "paused":
            self.status = "running"
            self._pause_event.set()
            self.emit_log("Discovery resumed")

    def stop(self) -> None:
        """Stop the running/paused discovery."""
        if self.status in ("running", "paused"):
            self.status = "stopped"
            self._pause_event.set()  # Unblock any waiting coroutine
            self.emit_log("Discovery stopped by user", level="warning")

    def reset(self) -> None:
        """Reset state back to idle after completion or stop."""
        self.status = "idle"
        self._pause_event.set()
        self.current_run_id = None

    def emit_log(self, message: str, level: str = "info") -> None:
        """Append a timestamped log entry to the deque."""
        entry = {
            "index": self._log_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "level": level,
        }
        self._logs.append(entry)
        self._log_index += 1

    def get_status(self) -> dict:
        """Return current discovery state as a dict."""
        return {
            "status": self.status,
            "progress_count": self.progress_count,
            "max_count": self.max_count,
            "current_run_id": self.current_run_id,
        }

    def check_should_stop(self) -> bool:
        """Return True if the discovery should stop."""
        return self.status in ("stopped",)

    async def wait_if_paused(self) -> None:
        """Block until the pause event is set (unpaused)."""
        await self._pause_event.wait()

    def get_logs(self, since_index: int = 0) -> list:
        """Return log entries with index > since_index."""
        return [entry for entry in self._logs if entry["index"] > since_index]

    def increment_progress(self) -> None:
        """Increment the discovered profile counter."""
        self.progress_count += 1


# Module-level singleton
discovery_state = DiscoveryState()
