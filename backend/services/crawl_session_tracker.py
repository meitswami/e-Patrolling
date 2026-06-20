"""Track live crawl activity and system performance for a single crawl session."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from services.system_metrics_collector import collect_metrics, collect_system_specs
from utils.logger import get_logger

logger = get_logger(__name__)

SPIKE_THRESHOLD = 95.0
SAMPLE_INTERVAL_SEC = 3.0

_sessions: dict[str, "CrawlSessionState"] = {}


@dataclass
class CrawlSessionState:
    log_id: UUID
    activity_log: list[dict[str, Any]] = field(default_factory=list)
    spikes: list[dict[str, Any]] = field(default_factory=list)
    samples: list[dict[str, Any]] = field(default_factory=list)
    system_specs: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sample_task: Optional[asyncio.Task] = None


def _metric_snapshot() -> dict[str, Any]:
    metrics = collect_metrics(use_cache=False)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ram_percent": metrics["ram"]["percent"],
        "swap_percent": metrics["swap"]["percent"],
        "cpu_percent": metrics["cpu"]["percent"],
        "disk_percent": metrics["disk"]["percent"],
        "ram_used_mb": metrics["ram"]["used_mb"],
        "ram_total_mb": metrics["ram"]["total_mb"],
        "bandwidth_rx_kbps": metrics["bandwidth"]["rx_kbps"],
        "bandwidth_tx_kbps": metrics["bandwidth"]["tx_kbps"],
    }


def _check_spikes(state: CrawlSessionState, snap: dict[str, Any]) -> None:
    checks = [
        ("RAM", snap["ram_percent"]),
        ("SWAP", snap["swap_percent"]),
        ("CPU", snap["cpu_percent"]),
        ("DISK", snap["disk_percent"]),
    ]
    ts = snap["timestamp"]
    for metric, value in checks:
        if value >= SPIKE_THRESHOLD:
            state.spikes.append(
                {
                    "metric": metric,
                    "value": value,
                    "threshold": SPIKE_THRESHOLD,
                    "timestamp": ts,
                }
            )


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _peak(values: list[float]) -> float:
    return round(max(values), 1) if values else 0.0


async def _sample_loop(session_key: str) -> None:
    try:
        while session_key in _sessions:
            await asyncio.sleep(SAMPLE_INTERVAL_SEC)
            state = _sessions.get(session_key)
            if not state:
                break
            snap = _metric_snapshot()
            state.samples.append(snap)
            _check_spikes(state, snap)
    except asyncio.CancelledError:
        pass


async def start_tracking(log_id: UUID) -> None:
    """Begin sampling system metrics and prepare activity log storage."""
    key = str(log_id)
    if key in _sessions:
        await stop_tracking(log_id)

    state = CrawlSessionState(log_id=log_id)
    state.system_specs = collect_system_specs()
    state.samples.append(_metric_snapshot())
    state.sample_task = asyncio.create_task(_sample_loop(key))
    _sessions[key] = state
    logger.debug("Crawl session tracking started for log %s", log_id)


def record_activity(log_id: UUID, event: dict[str, Any]) -> None:
    """Append a live crawl activity event to the session log."""
    state = _sessions.get(str(log_id))
    if state:
        state.activity_log.append(event)


async def stop_tracking(log_id: UUID) -> dict[str, Any]:
    """Stop sampling and return session_data payload for persistence."""
    key = str(log_id)
    state = _sessions.pop(key, None)
    if not state:
        return {}

    if state.sample_task:
        state.sample_task.cancel()
        try:
            await state.sample_task
        except asyncio.CancelledError:
            pass

    end_snap = _metric_snapshot()
    state.samples.append(end_snap)
    _check_spikes(state, end_snap)

    ram_vals = [s["ram_percent"] for s in state.samples]
    swap_vals = [s["swap_percent"] for s in state.samples]
    cpu_vals = [s["cpu_percent"] for s in state.samples]
    disk_vals = [s["disk_percent"] for s in state.samples]

    return {
        "activity_log": state.activity_log,
        "system_specs": state.system_specs,
        "performance": {
            "sample_count": len(state.samples),
            "sample_interval_sec": SAMPLE_INTERVAL_SEC,
            "spike_threshold_percent": SPIKE_THRESHOLD,
            "start_snapshot": state.samples[0] if state.samples else end_snap,
            "end_snapshot": end_snap,
            "peak": {
                "ram_percent": _peak(ram_vals),
                "swap_percent": _peak(swap_vals),
                "cpu_percent": _peak(cpu_vals),
                "disk_percent": _peak(disk_vals),
            },
            "average": {
                "ram_percent": _avg(ram_vals),
                "swap_percent": _avg(swap_vals),
                "cpu_percent": _avg(cpu_vals),
                "disk_percent": _avg(disk_vals),
            },
            "spikes": state.spikes,
        },
        "tracking_started_at": state.started_at.isoformat(),
        "tracking_stopped_at": datetime.now(timezone.utc).isoformat(),
    }
