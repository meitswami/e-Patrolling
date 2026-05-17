"""Patrol platform registry tests."""

from crawlers.registry import (
    is_patrol_platform,
    platform_catalog,
    supported_platforms,
)
from database.models import PlatformType


def test_supported_platforms_mvp_four():
    platforms = supported_platforms()
    assert set(platforms) == {"instagram", "facebook", "twitter", "threads"}


def test_is_patrol_platform():
    assert is_patrol_platform(PlatformType.INSTAGRAM) is True
    assert is_patrol_platform(PlatformType.TELEGRAM) is False


def test_platform_catalog_has_roadmap():
    catalog = platform_catalog()
    assert len(catalog["active"]) == 4
    roadmap_ids = {p["id"] for p in catalog["roadmap"]}
    assert "whatsapp" in roadmap_ids
    assert "linkedin" in roadmap_ids
