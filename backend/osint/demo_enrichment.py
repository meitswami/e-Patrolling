"""Shared demo-mode OSINT fields for synthetic crawl data."""

from __future__ import annotations

from typing import Any


def demo_profile_enrichment(accused_username: str, platform: str) -> dict[str, Any]:
    """Realistic public-profile fields for pipeline/OSINT testing in demo mode."""
    u = accused_username.lstrip("@")
    return {
        "source": "demo_mode",
        "accused_bio": f"Online troll · targets journalists · active on {platform}",
        "accused_avatar_url": f"https://i.pravatar.cc/150?u={platform}-{u}",
        "network_hints": {
            "geo_hints": ["Location from public bio (not IP)"],
            "timezone_hints": ["UTC+5:30"],
            "demo_network_hint": "Demo: platforms do not expose commenter IP to PATROL",
        },
    }
