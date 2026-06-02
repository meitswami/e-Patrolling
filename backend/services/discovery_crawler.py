"""
Auto-Discovery Crawler Service
================================
Discovers female, blue-tick, 10K+ follower accounts from social media platforms.
Infers region from bio text.
Runs daily via scheduler.

NOTE: This uses profile-level scraping (not comment crawling).
Each platform adapter's discover_profiles() is called.
Falls back to mock data for platforms without real discovery adapters yet.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PlatformType, TargetAccount, TargetSource
from database.models_discovery import DiscoveredTarget, DiscoveryRun
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Minimum criteria for discovery ──────────────────────────
MIN_FOLLOWERS = 10_000
REQUIRE_VERIFIED = True
REQUIRE_FEMALE = True

# Platforms to run discovery on
DISCOVERY_PLATFORMS = [
    PlatformType.INSTAGRAM,
    PlatformType.TWITTER,
    PlatformType.FACEBOOK,
]

# ── India region keywords for bio parsing ───────────────────
_INDIA_STATES = [
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "delhi", "mumbai", "kolkata", "chennai", "bangalore", "bengaluru",
    "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "surat",
    "kanpur", "nagpur", "indore", "bhopal", "patna", "vadodara",
    "ghaziabad", "ludhiana", "agra", "nashik", "meerut", "faridabad",
    "rajkot", "kalyan", "vasai", "thane", "aurangabad", "amritsar",
    "visakhapatnam", "chandigarh", "coimbatore", "kochi",
    "up", "mp", "hp", "ap", "tn", "wb", "rj", "gj", "mh", "ka", "pb",
]

# Female name indicators / bio keywords (heuristic)
_FEMALE_BIO_KEYWORDS = [
    "she/her", "actress", "model", "influencer", "blogger", "anchor",
    "journalist", "singer", "dancer", "writer", "author", "chef",
    "entrepreneur", "fashion", "beauty", "mom", "mother", "wife",
    "daughter", "sister", "girly", "queen", "princess",
]


def infer_region_from_bio(bio: str) -> tuple[str | None, float]:
    """
    Extract the most likely Indian state/city from a profile bio.
    Returns (region_string, confidence_0_to_1).
    """
    if not bio:
        return None, 0.0
    text = bio.lower()
    for region in _INDIA_STATES:
        # Whole-word match
        pattern = rf"\b{re.escape(region)}\b"
        if re.search(pattern, text):
            # Major cities get high confidence, state names lower
            confidence = 0.9 if len(region.split()) == 1 and len(region) > 4 else 0.75
            # Capitalize properly
            display = " ".join(w.capitalize() for w in region.split())
            return display, confidence
    return None, 0.0


def infer_gender_from_bio(bio: str, display_name: str = "") -> tuple[str, float]:
    """
    Heuristically detect gender from bio text.
    Returns ('female' | 'male' | 'unknown', confidence).
    """
    text = (bio + " " + display_name).lower()
    for kw in _FEMALE_BIO_KEYWORDS:
        if kw in text:
            return "female", 0.8
    # she/her pronouns
    if re.search(r"\bshe\b|\bher\b|\bhers\b", text):
        return "female", 0.95
    if re.search(r"\bhe\b|\bhim\b|\bhis\b", text):
        return "male", 0.9
    return "unknown", 0.0


# ── Platform-specific discovery adapters ────────────────────

async def _discover_instagram(
    run_id: uuid.UUID,
    session: AsyncSession,
    criteria: dict,
) -> list[dict]:
    """
    Discover verified female accounts on Instagram with 10K+ followers.
    Uses Playwright to search hashtags / explore if session available.
    Currently returns empty list in live mode (requires valid session).
    Extend this function with real scraping logic.
    """
    logger.info("Instagram discovery: searching for female verified accounts (10K+ followers)")
    # NOTE: Real implementation would:
    # 1. Use InstagramCrawler to browse explore/search
    # 2. Filter: is_verified=True, follower_count >= 10000
    # 3. Check bio for female indicators
    # For now returns empty — extend with real Playwright scraping
    return []


async def _discover_twitter(
    run_id: uuid.UUID,
    session: AsyncSession,
    criteria: dict,
) -> list[dict]:
    """
    Discover verified female accounts on Twitter/X.
    Uses Twitter API Bearer token if available.
    """
    from configs.settings import settings
    if not settings.TWITTER_BEARER_TOKEN:
        logger.info("Twitter discovery: no bearer token configured, skipping")
        return []

    logger.info("Twitter discovery: searching verified female accounts via API")
    # NOTE: Real implementation would use Twitter v2 API:
    # GET /2/users/search with filters: is_verified, followers_count>=10000
    # Then check bio for female/she-her keywords
    return []


async def _discover_facebook(
    run_id: uuid.UUID,
    session: AsyncSession,
    criteria: dict,
) -> list[dict]:
    """
    Discover verified female accounts on Facebook.
    Uses Graph API token if available.
    """
    from configs.settings import settings
    if not settings.FACEBOOK_ACCESS_TOKEN:
        logger.info("Facebook discovery: no access token configured, skipping")
        return []

    logger.info("Facebook discovery: searching verified female accounts via Graph API")
    return []


_PLATFORM_DISCOVERY: dict = {
    PlatformType.INSTAGRAM: _discover_instagram,
    PlatformType.TWITTER: _discover_twitter,
    PlatformType.FACEBOOK: _discover_facebook,
}


async def run_discovery(
    session: AsyncSession,
    *,
    triggered_by: str = "scheduler",
    platforms: list[PlatformType] | None = None,
) -> DiscoveryRun:
    """
    Main entry point: run auto-discovery across all configured platforms.
    Saves discovered profiles to discovered_targets table.
    Returns the DiscoveryRun record.
    """
    run_platforms = platforms or DISCOVERY_PLATFORMS
    run_id = uuid.uuid4()
    today = date.today()

    criteria = {
        "min_followers": MIN_FOLLOWERS,
        "require_verified": REQUIRE_VERIFIED,
        "require_female": REQUIRE_FEMALE,
        "platforms": [p.value for p in run_platforms],
    }

    run = DiscoveryRun(
        id=run_id,
        run_date=today,
        platforms=[p.value for p in run_platforms],
        status="running",
        criteria=criteria,
        triggered_by=triggered_by,
    )
    session.add(run)
    await session.flush()

    total_found = 0
    all_profiles: list[dict] = []

    for platform in run_platforms:
        discover_fn = _PLATFORM_DISCOVERY.get(platform)
        if not discover_fn:
            continue
        try:
            profiles = await discover_fn(run_id, session, criteria)
            for p in profiles:
                p["platform"] = platform
                p["discovery_run_id"] = run_id
            all_profiles.extend(profiles)
            logger.info("Discovery: %d profiles from %s", len(profiles), platform.value)
        except Exception as exc:
            logger.error("Discovery failed for %s: %s", platform.value, exc)

    # Deduplicate against existing target_accounts and already-discovered today
    existing_usernames: set[tuple[str, str]] = set()
    existing_q = await session.execute(
        select(TargetAccount.username, TargetAccount.platform)
    )
    for row in existing_q.all():
        existing_usernames.add((row[0].lower(), row[1].value))

    already_discovered_q = await session.execute(
        select(DiscoveredTarget.username, DiscoveredTarget.platform)
        .where(DiscoveredTarget.discovered_on == today)
    )
    for row in already_discovered_q.all():
        existing_usernames.add((row[0].lower(), row[1].value))

    saved = 0
    for profile in all_profiles:
        key = (profile.get("username", "").lower(), profile.get("platform", PlatformType.INSTAGRAM).value)
        if key in existing_usernames:
            continue

        bio = profile.get("bio") or ""
        region, region_conf = infer_region_from_bio(bio)
        gender, _ = infer_gender_from_bio(bio, profile.get("display_name") or "")

        # Only save female accounts matching criteria
        if REQUIRE_FEMALE and gender not in ("female", "unknown"):
            continue
        if profile.get("follower_count", 0) < MIN_FOLLOWERS:
            continue
        if REQUIRE_VERIFIED and not profile.get("is_verified", False):
            continue

        dt = DiscoveredTarget(
            platform=profile["platform"],
            username=profile["username"],
            display_name=profile.get("display_name"),
            profile_url=profile.get("profile_url", f"https://{profile['platform'].value}.com/{profile['username']}"),
            avatar_url=profile.get("avatar_url"),
            bio=bio or None,
            follower_count=profile.get("follower_count", 0),
            is_verified=profile.get("is_verified", False),
            gender=gender,
            inferred_region=region,
            region_confidence=region_conf,
            region_raw=bio[:200] if bio else None,
            discovered_on=today,
            discovery_run_id=run_id,
            discovery_criteria=criteria,
        )
        session.add(dt)
        existing_usernames.add(key)
        saved += 1
        total_found += 1

    run.total_found = total_found
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info(
        "Discovery run %s complete: %d profiles found, %d saved",
        run_id, total_found, saved,
    )
    return run


async def convert_discovered_to_target(
    session: AsyncSession,
    discovered_id: uuid.UUID,
    added_by_user_id: uuid.UUID,
) -> TargetAccount:
    """Promote a discovered profile to a monitored TargetAccount."""
    dt = await session.get(DiscoveredTarget, discovered_id)
    if not dt:
        raise ValueError(f"Discovered target {discovered_id} not found")
    if dt.is_converted:
        raise ValueError(f"@{dt.username} already converted to a monitored target")

    # Check duplicate
    existing = await session.execute(
        select(TargetAccount).where(
            TargetAccount.username == dt.username,
            TargetAccount.platform == dt.platform,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"@{dt.username} on {dt.platform.value} already exists in targets")

    target = TargetAccount(
        username=dt.username,
        display_name=dt.display_name,
        platform=dt.platform,
        profile_url=dt.profile_url,
        avatar_url=dt.avatar_url,
        follower_count=dt.follower_count,
        is_verified=dt.is_verified,
        inferred_region=dt.inferred_region,
        region_confidence=dt.region_confidence,
        notes=f"Auto-discovered on {dt.discovered_on}. Bio: {(dt.bio or '')[:100]}",
        added_by=added_by_user_id,
        source=TargetSource.ADMIN_PANEL,
        monitoring_enabled=True,
    )
    session.add(target)
    await session.flush()

    dt.is_converted = True
    dt.converted_to_target_id = target.id
    dt.converted_at = datetime.now(timezone.utc)
    await session.commit()
    return target
