"""Platform → crawler registry (active patrol vs roadmap)."""

from typing import Type

from crawlers.base_crawler import BaseCrawler
from crawlers.facebook.adapter import FacebookCrawler
from crawlers.instagram.adapter import InstagramCrawler
from crawlers.threads.adapter import ThreadsCrawler
from crawlers.twitter.adapter import TwitterCrawler
from database.models import PlatformType

# MVP patrol + monitoring (crawler + pipeline wired)
_ACTIVE: dict[PlatformType, Type[BaseCrawler]] = {
    PlatformType.INSTAGRAM: InstagramCrawler,
    PlatformType.TWITTER: TwitterCrawler,
    PlatformType.FACEBOOK: FacebookCrawler,
    PlatformType.THREADS: ThreadsCrawler,
}

# Shown in UI as planned — no crawler yet
_ROADMAP: list[dict[str, str]] = [
    {"id": "linkedin", "label": "LinkedIn", "status": "roadmap"},
    {"id": "telegram", "label": "Telegram", "status": "roadmap"},
    {"id": "whatsapp", "label": "WhatsApp", "status": "roadmap"},
    {"id": "signal", "label": "Signal", "status": "roadmap"},
    {"id": "threema", "label": "Threema", "status": "roadmap"},
]


def get_crawler_class(platform: PlatformType) -> Type[BaseCrawler]:
    if platform not in _ACTIVE:
        raise ValueError(
            f"Patrol not enabled for {platform.value}. "
            f"Active: {', '.join(supported_platforms())}"
        )
    return _ACTIVE[platform]


def supported_platforms() -> list[str]:
    """Platforms with working crawlers in this release."""
    return [p.value for p in _ACTIVE]


def is_patrol_platform(platform: PlatformType) -> bool:
    return platform in _ACTIVE


def platform_catalog() -> dict:
    """Full catalog for dashboard (active + roadmap)."""
    active = [
        {
            "id": p.value,
            "label": p.value.capitalize() if p != PlatformType.TWITTER else "Twitter / X",
            "status": "active",
            "patrol_enabled": True,
        }
        for p in _ACTIVE
    ]
    labels = {
        "instagram": "Instagram",
        "twitter": "Twitter / X",
        "facebook": "Facebook",
        "threads": "Threads",
    }
    for item in active:
        item["label"] = labels.get(item["id"], item["label"])
    return {"active": active, "roadmap": _ROADMAP}
