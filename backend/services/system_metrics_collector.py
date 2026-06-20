"""Shared system metrics collection for dashboard widget and crawl session tracking."""

import ctypes
import os
import platform
import shutil
import sys
import time
from typing import Optional

_IS_WINDOWS = sys.platform == "win32"

_cache: dict = {"data": None, "ts": 0.0}
_CACHE_TTL = 1.0

_prev_net: Optional[dict] = None
_prev_net_ts: float = 0.0


def _read_meminfo_linux() -> dict:
    info: dict[str, int] = {}
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


def _read_meminfo_windows() -> dict:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return {}

    total_kb = stat.ullTotalPhys // 1024
    avail_kb = stat.ullAvailPhys // 1024
    swap_total_kb = stat.ullTotalPageFile // 1024
    swap_free_kb = stat.ullAvailPageFile // 1024

    return {
        "MemTotal": total_kb,
        "MemAvailable": avail_kb,
        "SwapTotal": swap_total_kb,
        "SwapFree": swap_free_kb,
    }


def _read_meminfo() -> dict:
    if _IS_WINDOWS:
        return _read_meminfo_windows()
    return _read_meminfo_linux()


def _read_cpu_usage_linux() -> float:
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = line.split()
        if parts[0] != "cpu":
            return 0.0
        values = [int(x) for x in parts[1:9]]
        idle = values[3] + values[4]
        total = sum(values)

        prev = getattr(_read_cpu_usage_linux, "_prev", None)
        _read_cpu_usage_linux._prev = (idle, total)  # type: ignore[attr-defined]

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


def _read_cpu_usage_windows() -> float:
    idle = ctypes.c_ulonglong()
    kernel = ctypes.c_ulonglong()
    user = ctypes.c_ulonglong()
    if not ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        return 0.0

    idle_val = idle.value
    total_val = idle.value + kernel.value + user.value

    prev = getattr(_read_cpu_usage_windows, "_prev", None)
    _read_cpu_usage_windows._prev = (idle_val, total_val)  # type: ignore[attr-defined]

    if prev is None:
        return 0.0
    prev_idle, prev_total = prev
    d_idle = idle_val - prev_idle
    d_total = total_val - prev_total
    if d_total == 0:
        return 0.0
    return round((1.0 - d_idle / d_total) * 100, 1)


def _read_cpu_usage() -> float:
    if _IS_WINDOWS:
        return _read_cpu_usage_windows()
    return _read_cpu_usage_linux()


def _read_disk_usage() -> dict:
    path = (os.environ.get("SystemDrive", "C:") + "\\") if _IS_WINDOWS else "/"
    try:
        usage = shutil.disk_usage(path)
        total = usage.total
        used = usage.used
        free = usage.free
        percent = round((used / total) * 100, 1) if total > 0 else 0.0
        return {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "percent": percent,
        }
    except OSError:
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}


def _read_net_bytes_linux() -> dict:
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


def _read_net_bytes_windows() -> dict:
    from ctypes import wintypes

    class MIB_IF_ROW2(ctypes.Structure):
        _fields_ = [
            ("InterfaceLuid", ctypes.c_uint64),
            ("InterfaceIndex", wintypes.ULONG),
            ("InterfaceGuid", ctypes.c_byte * 16),
            ("Alias", wintypes.WCHAR * 257),
            ("Description", wintypes.WCHAR * 257),
            ("PhysicalAddressLength", wintypes.ULONG),
            ("PhysicalAddress", ctypes.c_byte * 32),
            ("PermanentPhysicalAddress", ctypes.c_byte * 32),
            ("Mtu", wintypes.ULONG),
            ("Type", wintypes.ULONG),
            ("TunnelType", wintypes.ULONG),
            ("MediaType", wintypes.ULONG),
            ("PhysicalMediumType", wintypes.ULONG),
            ("AccessType", wintypes.ULONG),
            ("DirectionType", wintypes.ULONG),
            ("InterfaceAndOperStatusFlags", wintypes.BYTE),
            ("OperStatus", wintypes.ULONG),
            ("AdminStatus", wintypes.ULONG),
            ("MediaConnectState", wintypes.ULONG),
            ("NetworkGuid", ctypes.c_byte * 16),
            ("ConnectionType", wintypes.ULONG),
            ("TransmitLinkSpeed", ctypes.c_uint64),
            ("ReceiveLinkSpeed", ctypes.c_uint64),
            ("InOctets", ctypes.c_uint64),
            ("InUcastPkts", ctypes.c_uint64),
            ("InNUcastPkts", ctypes.c_uint64),
            ("InDiscards", ctypes.c_uint64),
            ("InErrors", ctypes.c_uint64),
            ("InUnknownProtos", ctypes.c_uint64),
            ("InUcastOctets", ctypes.c_uint64),
            ("InMulticastOctets", ctypes.c_uint64),
            ("InBroadcastOctets", ctypes.c_uint64),
            ("OutOctets", ctypes.c_uint64),
            ("OutUcastPkts", ctypes.c_uint64),
            ("OutNUcastPkts", ctypes.c_uint64),
            ("OutDiscards", ctypes.c_uint64),
            ("OutErrors", ctypes.c_uint64),
            ("OutUcastOctets", ctypes.c_uint64),
            ("OutMulticastOctets", ctypes.c_uint64),
            ("OutBroadcastOctets", ctypes.c_uint64),
            ("OutQLen", ctypes.c_uint64),
        ]

    iphlpapi = ctypes.windll.iphlpapi
    size = wintypes.ULONG(0)
    iphlpapi.GetIfTable2Ex(1, ctypes.byref(size))
    if size.value == 0:
        return {"rx_bytes": 0, "tx_bytes": 0}

    buf = ctypes.create_string_buffer(size.value)
    if iphlpapi.GetIfTable2Ex(1, ctypes.byref(buf)) != 0:
        return {"rx_bytes": 0, "tx_bytes": 0}

    count = ctypes.cast(buf, ctypes.POINTER(wintypes.ULONG)).contents.value
    row_size = ctypes.sizeof(MIB_IF_ROW2)
    rx_total = 0
    tx_total = 0
    offset = ctypes.sizeof(wintypes.ULONG)
    for i in range(count):
        row = MIB_IF_ROW2.from_buffer_copy(buf, offset + i * row_size)
        if row.OperStatus == 1:
            rx_total += row.InOctets
            tx_total += row.OutOctets

    iphlpapi.FreeMibTable(ctypes.cast(buf, ctypes.c_void_p))
    return {"rx_bytes": rx_total, "tx_bytes": tx_total}


def _read_net_bytes() -> dict:
    if _IS_WINDOWS:
        try:
            return _read_net_bytes_windows()
        except Exception:
            return {"rx_bytes": 0, "tx_bytes": 0}
    return _read_net_bytes_linux()


def _calculate_bandwidth() -> dict:
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


def collect_metrics(*, use_cache: bool = True) -> dict:
    """Collect RAM, swap, CPU, disk, and bandwidth metrics."""
    now = time.time()
    if use_cache and _cache["data"] and (now - _cache["ts"]) < _CACHE_TTL:
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
        "cpu": {"percent": cpu},
        "disk": disk,
        "bandwidth": bandwidth,
        "timestamp": now,
    }

    if use_cache:
        _cache["data"] = data
        _cache["ts"] = now
    return data


def collect_system_specs() -> dict:
    """Static host specs captured at crawl start."""
    from datetime import datetime, timezone

    metrics = collect_metrics(use_cache=False)
    return {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "cpu_count": os.cpu_count() or 0,
        "processor": platform.processor() or "unknown",
        "ram_total_mb": metrics["ram"]["total_mb"],
        "disk_total_gb": metrics["disk"]["total_gb"],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
