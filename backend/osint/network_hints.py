"""Extract public network/location hints from crawl raw_data (not end-user IP)."""

from __future__ import annotations

from typing import Any

IP_DISCLAIMER = (
    "Social platforms do not expose a commenter's IP address to PATROL or other "
    "third-party monitors. Any IP-like values below are crawl-time infrastructure "
    "metadata or publicly stated location hints only — not verified identity."
)


def extract_network_hints(raw_data: dict[str, Any] | None) -> dict[str, Any]:
    """
    Collect non-invasive metadata captured during crawl.
    Real user IPs are not available from IG/FB/Twitter/Threads APIs.
    """
    raw = raw_data or {}
    hints: dict[str, Any] = {
        "disclaimer": IP_DISCLAIMER,
        "ip_addresses": [],
        "geo_hints": [],
        "timezone_hints": [],
        "user_agent": None,
        "proxy_detected": False,
    }

    nh = raw.get("network_hints")
    if isinstance(nh, dict):
        for key in ("ip_addresses", "geo_hints", "timezone_hints"):
            val = nh.get(key)
            if isinstance(val, list):
                hints[key] = val[:10]
        hints["user_agent"] = nh.get("user_agent")
        hints["proxy_detected"] = bool(nh.get("proxy_detected"))

    if raw.get("inferred_country"):
        hints["geo_hints"].append(str(raw["inferred_country"]))
    if raw.get("inferred_city"):
        hints["geo_hints"].append(str(raw["inferred_city"]))
    if raw.get("timezone"):
        hints["timezone_hints"].append(str(raw["timezone"]))

    # Demo / development synthetic hints (clearly labeled)
    if raw.get("source") == "demo_mode" and raw.get("demo_network_hint"):
        hints["demo_labeled"] = True
        hints["geo_hints"].append(str(raw["demo_network_hint"]))

    return hints


def merge_network_hints(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge hints from multiple evidence rows."""
    merged: dict[str, Any] = {
        "disclaimer": IP_DISCLAIMER,
        "ip_addresses": [],
        "geo_hints": [],
        "timezone_hints": [],
        "sources": len(records),
    }
    seen_ip: set[str] = set()
    seen_geo: set[str] = set()
    for rec in records:
        for ip in rec.get("ip_addresses") or []:
            if ip not in seen_ip:
                seen_ip.add(ip)
                merged["ip_addresses"].append(ip)
        for g in rec.get("geo_hints") or []:
            if g not in seen_geo:
                seen_geo.add(g)
                merged["geo_hints"].append(g)
        for tz in rec.get("timezone_hints") or []:
            if tz not in merged["timezone_hints"]:
                merged["timezone_hints"].append(tz)
    return merged
