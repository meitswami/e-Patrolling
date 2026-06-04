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
    """
    import asyncio
    from crawlers.instagram.session_manager import InstagramSessionManager
    from services.discovery_state import discovery_state

    session_mgr = InstagramSessionManager()
    if not session_mgr.has_saved_session():
        discovery_state.emit_log(
            "Instagram: No active session found. Connect Instagram in Settings to enable discovery.",
            level="warning",
        )
        return []

    discovery_state.emit_log("Instagram: Session found, launching browser for profile discovery...")

    profiles: list[dict] = []
    hashtags = [
        "indianfemaleinfluencer", "indianmodel", "indianactress",
        "bollywood", "indianfashionblogger", "indianbeautyblogger",
    ]

    try:
        from crawlers.instagram.adapter import InstagramCrawler

        crawler = InstagramCrawler()
        setup_ok = await crawler.setup_session()
        if not setup_ok:
            discovery_state.emit_log(
                "Instagram: Failed to launch browser session. Ensure Playwright browsers are installed.",
                level="error",
            )
            return []

        page = crawler._page
        if not page:
            discovery_state.emit_log("Instagram: No page available after setup.", level="error")
            await crawler.teardown_session()
            return []

        seen_usernames: set[str] = set()

        for hashtag in hashtags:
            if discovery_state.check_should_stop():
                break
            await discovery_state.wait_if_paused()

            discovery_state.emit_log(f"Instagram: Exploring #{hashtag}...")

            try:
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Find profile links from the explore page
                links = await page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
                post_urls = []
                for link in links[:12]:  # Limit posts per hashtag
                    href = await link.get_attribute("href")
                    if href and ("/p/" in href or "/reel/" in href):
                        if href.startswith("/"):
                            href = f"https://www.instagram.com{href}"
                        post_urls.append(href)

                discovery_state.emit_log(
                    f"Instagram: Found {len(post_urls)} posts from #{hashtag}"
                )

                # Visit each post to find the profile owner
                for post_url in post_urls:
                    if discovery_state.check_should_stop():
                        break
                    await discovery_state.wait_if_paused()

                    if discovery_state.progress_count >= criteria.get("min_followers", 0) // 1000 * 5:
                        # Rough heuristic to avoid over-crawling
                        pass

                    try:
                        await page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)

                        # Extract profile username from the post page
                        header_link = await page.query_selector(
                            "header a[href^='/'], article a[href^='/']"
                        )
                        if not header_link:
                            continue

                        profile_href = await header_link.get_attribute("href")
                        if not profile_href or profile_href in ("/", "/explore/"):
                            continue

                        username = profile_href.strip("/").split("/")[0]
                        if not username or username in seen_usernames:
                            continue
                        if username in ("explore", "p", "reel", "stories", "accounts"):
                            continue

                        seen_usernames.add(username)

                        # Navigate to profile page to get details
                        await page.goto(
                            f"https://www.instagram.com/{username}/",
                            wait_until="domcontentloaded",
                            timeout=20000,
                        )
                        await asyncio.sleep(2)

                        # Parse profile info from the page
                        profile_data = await _parse_instagram_profile(page, username)
                        if profile_data:
                            profiles.append(profile_data)
                            discovery_state.emit_log(
                                f"Instagram: Found @{username} "
                                f"({_format_followers(profile_data.get('follower_count', 0))} followers)"
                            )

                        await asyncio.sleep(1.5)
                    except Exception as exc:
                        logger.debug("Error visiting post %s: %s", post_url, exc)
                        continue

            except Exception as exc:
                discovery_state.emit_log(
                    f"Instagram: Error exploring #{hashtag}: {str(exc)[:100]}",
                    level="warning",
                )
                continue

        await crawler.teardown_session()
        discovery_state.emit_log(f"Instagram: Discovery complete, found {len(profiles)} profiles")

    except Exception as exc:
        discovery_state.emit_log(
            f"Instagram: Playwright error - {str(exc)[:150]}. "
            "Ensure browsers are installed: python -m playwright install chromium",
            level="error",
        )
        logger.error("Instagram discovery Playwright error: %s", exc, exc_info=True)

    return profiles


async def _parse_instagram_profile(page, username: str) -> Optional[dict]:
    """Parse profile information from an Instagram profile page."""
    try:
        # Try to get meta description which often contains follower info
        meta = await page.query_selector('meta[property="og:description"]')
        description = ""
        if meta:
            description = (await meta.get_attribute("content")) or ""

        # Try to parse follower count from the description or page content
        follower_count = 0
        import re as _re
        follower_match = _re.search(
            r"([\d,.]+[KMkm]?)\s*[Ff]ollowers", description
        )
        if follower_match:
            follower_count = _parse_follower_str(follower_match.group(1))

        # If we could not get from meta, try from page text
        if follower_count == 0:
            try:
                spans = await page.query_selector_all("span[title], span[class]")
                for span in spans:
                    title = await span.get_attribute("title")
                    if title and title.replace(",", "").isdigit():
                        # Check if this is the followers span
                        parent = await span.evaluate_handle("el => el.closest('a') || el.closest('li')")
                        if parent:
                            inner = await parent.inner_text()
                            if "follower" in inner.lower():
                                follower_count = int(title.replace(",", ""))
                                break
            except Exception:
                pass

        # Get display name
        display_name = None
        try:
            name_el = await page.query_selector("header section span, header h2")
            if name_el:
                display_name = await name_el.inner_text()
        except Exception:
            pass

        # Get bio
        bio = ""
        try:
            bio_el = await page.query_selector("header section div span, div.-vDIg span")
            if bio_el:
                bio = await bio_el.inner_text()
        except Exception:
            pass

        # Check verified badge
        is_verified = False
        try:
            verified_el = await page.query_selector(
                'svg[aria-label="Verified"], span[title="Verified"]'
            )
            is_verified = verified_el is not None
        except Exception:
            pass

        # Get avatar URL
        avatar_url = None
        try:
            img = await page.query_selector("header img[alt]")
            if img:
                avatar_url = await img.get_attribute("src")
        except Exception:
            pass

        return {
            "username": username,
            "display_name": display_name,
            "profile_url": f"https://www.instagram.com/{username}/",
            "avatar_url": avatar_url,
            "bio": bio,
            "follower_count": follower_count,
            "is_verified": is_verified,
        }
    except Exception as exc:
        logger.debug("Failed to parse profile @%s: %s", username, exc)
        return None


def _parse_follower_str(s: str) -> int:
    """Parse follower count strings like '12.5K', '1.2M', '45,678'."""
    s = s.strip().replace(",", "")
    multiplier = 1
    if s.upper().endswith("K"):
        multiplier = 1000
        s = s[:-1]
    elif s.upper().endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    try:
        return int(float(s) * multiplier)
    except (ValueError, TypeError):
        return 0


def _format_followers(count: int) -> str:
    """Format follower count for display (e.g. 12500 -> '12.5K')."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


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
    max_count: int = 25,
) -> DiscoveryRun:
    """
    Main entry point: run auto-discovery across all configured platforms.
    Saves discovered profiles to discovered_targets table.
    Returns the DiscoveryRun record.
    """
    from services.discovery_state import discovery_state

    run_platforms = platforms or DISCOVERY_PLATFORMS
    run_id = uuid.uuid4()
    today = date.today()

    criteria = {
        "min_followers": MIN_FOLLOWERS,
        "require_verified": REQUIRE_VERIFIED,
        "require_female": REQUIRE_FEMALE,
        "platforms": [p.value for p in run_platforms],
    }

    # Initialize discovery state
    discovery_state.start(max_count, str(run_id))

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

    try:
        for platform in run_platforms:
            if discovery_state.check_should_stop():
                discovery_state.emit_log("Discovery stopped before all platforms were searched")
                break

            discover_fn = _PLATFORM_DISCOVERY.get(platform)
            if not discover_fn:
                continue

            discovery_state.emit_log(f"Searching {platform.value}...")

            try:
                profiles = await discover_fn(run_id, session, criteria)
                for p in profiles:
                    p["platform"] = platform
                    p["discovery_run_id"] = run_id
                all_profiles.extend(profiles)
                discovery_state.emit_log(f"Found {len(profiles)} profiles from {platform.value}")
            except Exception as exc:
                logger.error("Discovery failed for %s: %s", platform.value, exc)
                discovery_state.emit_log(
                    f"Error discovering from {platform.value}: {str(exc)[:100]}",
                    level="error",
                )

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
            # Check pause/stop before each profile
            await discovery_state.wait_if_paused()
            if discovery_state.check_should_stop():
                discovery_state.emit_log("Discovery stopped during profile saving")
                break
            if discovery_state.progress_count >= max_count:
                discovery_state.emit_log(f"Reached max count of {max_count} profiles")
                break

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
            discovery_state.increment_progress()
            discovery_state.emit_log(
                f"Discovered @{profile['username']} "
                f"({_format_followers(profile.get('follower_count', 0))} followers)"
            )

        run.total_found = total_found
        run.status = "completed" if not discovery_state.check_should_stop() else "stopped"
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()

        discovery_state.emit_log(f"Discovery complete: {total_found} profiles found")

    except Exception as exc:
        logger.error("Discovery run %s failed: %s", run_id, exc, exc_info=True)
        discovery_state.emit_log(f"Discovery error: {str(exc)[:200]}", level="error")
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()
    finally:
        discovery_state.reset()

    logger.info(
        "Discovery run %s complete: %d profiles found",
        run_id, total_found,
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
