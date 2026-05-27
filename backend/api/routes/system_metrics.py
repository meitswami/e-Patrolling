"""Live system performance metrics endpoint for dashboard monitoring widget."""

import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Depends

from auth.middleware import get_current_user
from database.models import User
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Cache metrics for 1 second to avoid excessive /proc reads
_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 1.0

# Track bandwidth (bytes read between calls)
_prev_net: Optional[dict] = None
_prev_net_ts: float = 0.0


def _read_meminfo() -> dict:
    """Read /proc/meminfo (Linux only)."""
    info = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    value_kb = int(parts[1])
                    info[key] = value_kb
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    return info


def _read_cpu_usage() -> float:
    """Read /proc/stat for overall CPU usage percentage."""
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = line.split()
        if parts[0] != "cpu":
            return 0.0
        # user, nice, system, idle, iowait, irq, softirq, steal
        values = [int(x) for x in parts[1:9]]
        idle = values[3] + values[4]  # idle + iowait
        total = sum(values)

        # Need two samples — use a simple stored previous
        prev = getattr(_read_cpu_usage, "_prev", None)
        _read_cpu_usage._prev = (idle, total)  # type: ignore

        if prev is None:
            return 0.0
        prev_idle, prev_total = prev
        d_idle = idle - prev_idle
        d_total = total - prev_total
        if d_total == 0:
            return 0.0
        return round((1.0 - d_idle / d_total) * 100, 1)
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        return 0.0


def _read_disk_usage() -> dict:
    """Read disk usage for root filesystem via statvfs."""
    import os

    try:
        st = os.statvfs("/")
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        used = total - free
        percent = round((used / total) * 100, 1) if total > 0 else 0.0
        return {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "percent": percent,
        }
    except (OSError, ZeroDivisionError):
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}


def _read_net_bytes() -> dict:
    """Read /proc/net/dev for total rx/tx bytes."""
    rx_total = 0
    tx_total = 0
    try:
        with open("/proc/net/dev", "r") as f:
            for line in f:
                if ":" not in line:
                    continue
                iface, data = line.split(":", 1)
                iface = iface.strip()
                if iface == "lo":
                    continue
                parts = data.split()
                if len(parts) >= 9:
                    rx_total += int(parts[0])
                    tx_total += int(parts[8])
    except (FileNotFoundError, PermissionError, ValueError):
        pass
    return {"rx_bytes": rx_total, "tx_bytes": tx_total}


def _calculate_bandwidth() -> dict:
    """Calculate bandwidth in KB/s since last call."""
    global _prev_net, _prev_net_ts

    now = time.time()
    current = _read_net_bytes()

    if _prev_net is None:
        _prev_net = current
        _prev_net_ts = now
        return {"rx_kbps": 0.0, "tx_kbps": 0.0}

    elapsed = now - _prev_net_ts
    if elapsed < 0.1:
        return {"rx_kbps": 0.0, "tx_kbps": 0.0}

    rx_diff = current["rx_bytes"] - _prev_net["rx_bytes"]
    tx_diff = current["tx_bytes"] - _prev_net["tx_bytes"]

    rx_kbps = round((rx_diff / elapsed) / 1024, 1)
    tx_kbps = round((tx_diff / elapsed) / 1024, 1)

    _prev_net = current
    _prev_net_ts = now

    return {"rx_kbps": max(0, rx_kbps), "tx_kbps": max(0, tx_kbps)}


def _collect_metrics() -> dict:
    """Collect all system metrics."""
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["data"]

    mem = _read_meminfo()
    total_kb = mem.get("MemTotal", 0)
    available_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
    used_kb = total_kb - available_kb
    ram_percent = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0

    swap_total_kb = mem.get("SwapTotal", 0)
    swap_free_kb = mem.get("SwapFree", 0)
    swap_used_kb = swap_total_kb - swap_free_kb
    swap_percent = round((swap_used_kb / swap_total_kb) * 100, 1) if swap_total_kb > 0 else 0

    cpu = _read_cpu_usage()
    disk = _read_disk_usage()
    bandwidth = _calculate_bandwidth()

    data = {
        "ram": {
            "total_mb": round(total_kb / 1024, 0),
            "used_mb": round(used_kb / 1024, 0),
            "available_mb": round(available_kb / 1024, 0),
            "percent": ram_percent,
        },
        "swap": {
            "total_mb": round(swap_total_kb / 1024, 0),
            "used_mb": round(swap_used_kb / 1024, 0),
            "free_mb": round(swap_free_kb / 1024, 0),
            "percent": swap_percent,
        },
        "cpu": {
            "percent": cpu,
        },
        "disk": disk,
        "bandwidth": bandwidth,
        "timestamp": now,
    }

    _cache["data"] = data
    _cache["ts"] = now
    return data


@router.get("/system-stats")
async def get_system_stats(
    _user: User = Depends(get_current_user),
) -> dict:
    """Real-time system performance metrics (RAM, Swap, CPU, Disk, Bandwidth)."""
    return _collect_metrics()
