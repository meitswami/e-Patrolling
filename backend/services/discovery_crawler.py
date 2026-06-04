"""
Auto-Discovery Crawler Service
================================
Discovers social media accounts based on configurable criteria:
- Follower thresholds (min/max)
- Gender filter
- Verification status
- Region targeting
- Custom hashtags and content types

Supports Instagram web API with fallback to Playwright DOM scraping.
Runs on a configurable schedule or via manual trigger.
"""

from __future__ import annotations

import random
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

# ── Default platforms for discovery ─────────────────────────
DISCOVERY_PLATFORMS = [
    PlatformType.INSTAGRAM,
    PlatformType.TWITTER,
    PlatformType.FACEBOOK,
]

# ── Content type to hashtag mapping ─────────────────────────
CONTENT_TYPE_HASHTAGS: dict[str, list[str]] = {
    "Model": ["indianmodel", "indiansupermodel", "modelindia", "indianfashionmodel", "modelphotoshoot"],
    "Actor": ["indianactress", "bollywoodactress", "indianactor", "tollywoodactress", "kollywoodactress"],
    "Influencer": ["indianinfluencer", "indianfemaleinfluencer", "influencerindia", "contentcreatorindia"],
    "Blogger": ["indianblogger", "indianfashionblogger", "indianbeautyblogger", "lifestyleblogger"],
    "Singer": ["indiansinger", "bollywoodsinger", "playbacksinger", "indianmusician"],
    "Dancer": ["indiandancer", "classicaldancer", "bollywooddancer", "dancersofindia"],
    "Journalist": ["indianjournalist", "newsanchor", "mediapersonality", "indianmedia"],
    "Sportsperson": ["indiansportswomen", "indianathlete", "womeninsports", "sportsindia"],
}

# ── Major Indian cities (50+) ──────────────────────────────
INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Ahmedabad",
    "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna",
    "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad",
    "Meerut", "Rajkot", "Kalyan", "Vasai", "Varanasi", "Srinagar",
    "Aurangabad", "Dhanbad", "Amritsar", "Navi Mumbai", "Allahabad",
    "Ranchi", "Howrah", "Coimbatore", "Jabalpur", "Gwalior",
    "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kochi",
    "Chandigarh", "Thiruvananthapuram", "Dehradun", "Mysore", "Mysuru",
    "Gurgaon", "Gurugram", "Noida", "Bhubaneswar", "Mangalore",
    "Udaipur", "Jamshedpur", "Shimla", "Surat", "Tiruchirappalli",
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

# Instagram web app ID - used for API requests. Update if Instagram rotates this.
IG_WEB_APP_ID = "936619743392459"


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


def _build_hashtags_from_options(
    hashtags: list[str] | None,
    content_types: list[str] | None,
) -> list[str]:
    """Build the list of hashtags to search based on user options."""
    result: list[str] = []

    if hashtags:
        result.extend(hashtags)

    if content_types:
        for ct in content_types:
            mapped = CONTENT_TYPE_HASHTAGS.get(ct, [])
            result.extend(mapped)

    if not result:
        # Default hashtags
        result = [
            "indianfemaleinfluencer", "indianmodel", "indianactress",
            "bollywood", "indianfashionblogger", "indianbeautyblogger",
        ]

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for h in result:
        h_lower = h.lower().strip().lstrip("#")
        if h_lower not in seen:
            seen.add(h_lower)
            deduped.append(h_lower)
    return deduped


# ── Platform-specific discovery adapters ────────────────────

async def _discover_instagram(
    run_id: uuid.UUID,
    session: AsyncSession,
    criteria: dict,
) -> list[dict]:
    """
    Discover accounts on Instagram matching criteria.
    Strategy:
      1. Try Instagram web API endpoints (faster, more reliable)
      2. Fall back to Playwright DOM scraping if API fails
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

    discovery_state.emit_log("Instagram: Session found, attempting API-based discovery...")

    hashtags = _build_hashtags_from_options(
        criteria.get("hashtags"),
        criteria.get("content_types"),
    )

    profiles: list[dict] = []
    api_success = False

    # Strategy 1: Instagram Web API approach
    try:
        api_profiles = await _discover_instagram_api(
            session_mgr, hashtags, criteria, discovery_state
        )
        if api_profiles:
            profiles.extend(api_profiles)
            api_success = True
            discovery_state.emit_log(
                f"Instagram API: Found {len(api_profiles)} profiles via web API"
            )
    except Exception as exc:
        discovery_state.emit_log(
            f"Instagram API: Failed ({str(exc)[:100]}), falling back to browser...",
            level="warning",
        )
        logger.warning("Instagram API discovery failed: %s", exc)

    # Strategy 2: Fallback to Playwright DOM scraping
    if not api_success:
        discovery_state.emit_log("Instagram: Using browser-based discovery (fallback)...")
        try:
            dom_profiles = await _discover_instagram_dom(
                hashtags, criteria, discovery_state
            )
            profiles.extend(dom_profiles)
        except Exception as exc:
            discovery_state.emit_log(
                f"Instagram DOM: Playwright error - {str(exc)[:150]}",
                level="error",
            )
            logger.error("Instagram DOM discovery error: %s", exc, exc_info=True)

    discovery_state.emit_log(f"Instagram: Discovery complete, found {len(profiles)} profiles")
    return profiles


async def _discover_instagram_api(
    session_mgr,
    hashtags: list[str],
    criteria: dict,
    discovery_state,
) -> list[dict]:
    """
    Use Instagram web API endpoints to discover profiles from hashtags.
    Endpoints:
      - /api/v1/tags/web_info/?tag_name={tag} - get posts for a hashtag
      - /api/v1/users/web_profile_info/?username={user} - get profile info
    """
    import asyncio
    import json as json_mod

    import httpx

    profiles: list[dict] = []
    seen_usernames: set[str] = set()

    # Load session cookies if available
    cookies = {}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-IG-App-ID": IG_WEB_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }

    # Try to load cookies from saved session using the public session_path attribute
    try:
        session_file = session_mgr.session_path
        if session_file and session_file.exists():
            data = json_mod.loads(session_file.read_text())
            if isinstance(data, dict) and "cookies" in data:
                for cookie in data["cookies"]:
                    if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                        cookies[cookie["name"]] = cookie["value"]
            elif isinstance(data, list):
                for cookie in data:
                    if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                        cookies[cookie["name"]] = cookie["value"]
    except Exception as exc:
        logger.debug("Could not load Instagram session cookies: %s", exc)

    if not cookies:
        # Try alternate session file path using absolute path from settings
        try:
            from configs.settings import settings
            fallback_path = settings.EVIDENCE_STORAGE_PATH.parent / "sessions" / "instagram_state.json"
            if fallback_path.exists():
                data = json_mod.loads(fallback_path.read_text())
                if isinstance(data, dict) and "cookies" in data:
                    for cookie in data["cookies"]:
                        if isinstance(cookie, dict) and "name" in cookie:
                            cookies[cookie["name"]] = cookie["value"]
        except Exception:
            pass

    async with httpx.AsyncClient(
        headers=headers,
        cookies=cookies,
        timeout=httpx.Timeout(15.0),
        follow_redirects=True,
    ) as client:
        for hashtag in hashtags:
            if discovery_state.check_should_stop():
                break
            await discovery_state.wait_if_paused()

            discovery_state.emit_log(f"Instagram API: Fetching #{hashtag}...")

            try:
                # Fetch hashtag info with top posts
                tag_url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={hashtag}"
                resp = await client.get(tag_url)

                if resp.status_code != 200:
                    discovery_state.emit_log(
                        f"Instagram API: #{hashtag} returned status {resp.status_code}",
                        level="warning",
                    )
                    # Rate limited or blocked - stop API approach
                    if resp.status_code in (401, 403, 429):
                        raise Exception(f"API blocked with status {resp.status_code}")
                    continue

                tag_data = resp.json()

                # Extract usernames from top/recent posts
                usernames_to_check: list[str] = []
                # Navigate the response structure for media items
                sections = (
                    tag_data.get("data", {}).get("top", {}).get("sections", [])
                    or tag_data.get("data", {}).get("recent", {}).get("sections", [])
                    or []
                )
                for section in sections:
                    medias = section.get("layout_content", {}).get("medias", [])
                    for media_item in medias:
                        media = media_item.get("media", {})
                        user = media.get("user", {})
                        username = user.get("username")
                        if username and username not in seen_usernames:
                            usernames_to_check.append(username)
                            seen_usernames.add(username)

                # Also try flat media list
                if not usernames_to_check:
                    top_posts = tag_data.get("top_posts", []) or tag_data.get("ranked_items", [])
                    for post in top_posts:
                        user = post.get("user", {}) or post.get("owner", {})
                        username = user.get("username")
                        if username and username not in seen_usernames:
                            usernames_to_check.append(username)
                            seen_usernames.add(username)

                discovery_state.emit_log(
                    f"Instagram API: Found {len(usernames_to_check)} users from #{hashtag}"
                )

                # Fetch profile info for each user
                for username in usernames_to_check[:15]:  # Limit per hashtag
                    if discovery_state.check_should_stop():
                        break
                    await discovery_state.wait_if_paused()

                    # Random delay between requests (2-5 seconds)
                    await asyncio.sleep(random.uniform(2.0, 5.0))

                    try:
                        profile_url = (
                            f"https://www.instagram.com/api/v1/users/web_profile_info/"
                            f"?username={username}"
                        )
                        profile_resp = await client.get(profile_url)

                        if profile_resp.status_code != 200:
                            continue

                        profile_data = profile_resp.json()
                        user_data = profile_data.get("data", {}).get("user", {})
                        if not user_data:
                            user_data = profile_data.get("user", {})
                        if not user_data:
                            continue

                        follower_count = user_data.get("edge_followed_by", {}).get("count", 0)
                        if not follower_count:
                            follower_count = user_data.get("follower_count", 0)

                        is_verified = user_data.get("is_verified", False)
                        full_name = user_data.get("full_name", "")
                        bio = user_data.get("biography", "")
                        avatar = user_data.get("profile_pic_url_hd") or user_data.get("profile_pic_url", "")

                        profiles.append({
                            "username": username,
                            "display_name": full_name or None,
                            "profile_url": f"https://www.instagram.com/{username}/",
                            "avatar_url": avatar or None,
                            "bio": bio,
                            "follower_count": follower_count,
                            "is_verified": is_verified,
                        })

                        discovery_state.emit_log(
                            f"Instagram API: @{username} "
                            f"({_format_followers(follower_count)} followers)"
                        )

                    except Exception as exc:
                        logger.debug("Error fetching profile @%s: %s", username, exc)
                        continue

            except Exception as exc:
                if "API blocked" in str(exc):
                    raise
                discovery_state.emit_log(
                    f"Instagram API: Error on #{hashtag}: {str(exc)[:100]}",
                    level="warning",
                )
                continue

            # Random delay between hashtags
            await asyncio.sleep(random.uniform(2.0, 4.0))

    return profiles


async def _discover_instagram_dom(
    hashtags: list[str],
    criteria: dict,
    discovery_state,
) -> list[dict]:
    """
    Fallback: Discover profiles by visiting hashtag pages with Playwright.
    """
    import asyncio

    from crawlers.instagram.adapter import InstagramCrawler

    profiles: list[dict] = []
    seen_usernames: set[str] = set()

    try:
        crawler = InstagramCrawler()
        setup_ok = await crawler.setup_session()
        if not setup_ok:
            discovery_state.emit_log(
                "Instagram DOM: Failed to launch browser session.",
                level="error",
            )
            return []

        page = crawler._page
        if not page:
            discovery_state.emit_log("Instagram DOM: No page available after setup.", level="error")
            await crawler.teardown_session()
            return []

        for hashtag in hashtags:
            if discovery_state.check_should_stop():
                break
            await discovery_state.wait_if_paused()

            discovery_state.emit_log(f"Instagram DOM: Exploring #{hashtag}...")

            try:
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)

                # Find profile links from the explore page
                links = await page.query_selector_all("a[href*='/p/'], a[href*='/reel/']")
                post_urls = []
                for link in links[:12]:
                    href = await link.get_attribute("href")
                    if href and ("/p/" in href or "/reel/" in href):
                        if href.startswith("/"):
                            href = f"https://www.instagram.com{href}"
                        post_urls.append(href)

                discovery_state.emit_log(
                    f"Instagram DOM: Found {len(post_urls)} posts from #{hashtag}"
                )

                for post_url in post_urls:
                    if discovery_state.check_should_stop():
                        break
                    await discovery_state.wait_if_paused()

                    try:
                        await page.goto(post_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)

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

                        await page.goto(
                            f"https://www.instagram.com/{username}/",
                            wait_until="domcontentloaded",
                            timeout=20000,
                        )
                        await asyncio.sleep(2)

                        profile_data = await _parse_instagram_profile(page, username)
                        if profile_data:
                            profiles.append(profile_data)
                            discovery_state.emit_log(
                                f"Instagram DOM: Found @{username} "
                                f"({_format_followers(profile_data.get('follower_count', 0))} followers)"
                            )

                        # Random delay between profile visits
                        await asyncio.sleep(random.uniform(1.5, 3.5))
                    except Exception as exc:
                        logger.debug("Error visiting post %s: %s", post_url, exc)
                        continue

            except Exception as exc:
                discovery_state.emit_log(
                    f"Instagram DOM: Error exploring #{hashtag}: {str(exc)[:100]}",
                    level="warning",
                )
                continue

        await crawler.teardown_session()

    except Exception as exc:
        discovery_state.emit_log(
            f"Instagram DOM: Playwright error - {str(exc)[:150]}. "
            "Ensure browsers are installed: python -m playwright install chromium",
            level="error",
        )
        logger.error("Instagram DOM discovery error: %s", exc, exc_info=True)

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
    Discover verified accounts on Twitter/X.
    Uses Twitter API Bearer token if available.
    """
    from configs.settings import settings
    if not settings.TWITTER_BEARER_TOKEN:
        logger.info("Twitter discovery: no bearer token configured, skipping")
        return []

    logger.info("Twitter discovery: searching verified accounts via API")
    return []


async def _discover_facebook(
    run_id: uuid.UUID,
    session: AsyncSession,
    criteria: dict,
) -> list[dict]:
    """
    Discover verified accounts on Facebook.
    Uses Graph API token if available.
    """
    from configs.settings import settings
    if not settings.FACEBOOK_ACCESS_TOKEN:
        logger.info("Facebook discovery: no access token configured, skipping")
        return []

    logger.info("Facebook discovery: searching verified accounts via Graph API")
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
    platforms_str: list[str] | None = None,
    max_count: int = 25,
    min_followers: int = 10_000,
    max_followers: int | None = None,
    gender: str = "female",
    require_verified: bool = True,
    regions: list[str] | None = None,
    hashtags: list[str] | None = None,
    content_types: list[str] | None = None,
) -> DiscoveryRun:
    """
    Main entry point: run auto-discovery across configured platforms.
    Saves discovered profiles to discovered_targets table.
    Returns the DiscoveryRun record.

    All filtering criteria are now passed as parameters instead of
    using hardcoded constants.
    """
    from services.discovery_state import discovery_state

    # Resolve platforms from string list if provided
    if platforms_str and not platforms:
        platform_map = {p.value: p for p in PlatformType}
        platforms = [platform_map[p] for p in platforms_str if p in platform_map]

    run_platforms = platforms or DISCOVERY_PLATFORMS
    run_id = uuid.uuid4()
    today = date.today()

    criteria = {
        "min_followers": min_followers,
        "max_followers": max_followers,
        "require_verified": require_verified,
        "gender": gender,
        "platforms": [p.value for p in run_platforms],
        "regions": regions,
        "hashtags": hashtags,
        "content_types": content_types,
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

        # Deduplicate against existing target_accounts and ALL discovered_targets
        existing_usernames: set[tuple[str, str]] = set()
        existing_q = await session.execute(
            select(TargetAccount.username, TargetAccount.platform)
        )
        for row in existing_q.all():
            existing_usernames.add((row[0].lower(), row[1].value))

        # Check ALL DiscoveredTarget entries (not just today)
        already_discovered_q = await session.execute(
            select(DiscoveredTarget.username, DiscoveredTarget.platform)
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
            inferred_gender, _ = infer_gender_from_bio(bio, profile.get("display_name") or "")

            # Apply gender filter based on criteria
            if gender == "female" and inferred_gender not in ("female", "unknown"):
                continue
            elif gender == "male" and inferred_gender not in ("male", "unknown"):
                continue
            # gender == "all" passes everything through

            # Apply follower count filters
            profile_followers = profile.get("follower_count", 0)
            if profile_followers < min_followers:
                continue
            if max_followers is not None and profile_followers > max_followers:
                continue

            # Apply verification filter
            if require_verified and not profile.get("is_verified", False):
                continue

            # Apply region filter if specified
            # Note: If regions filter is specified, we only EXCLUDE profiles that are
            # detectably from a different region. Profiles with no detected region pass
            # through (fail-open) to avoid missing relevant profiles whose bios don't
            # mention location explicitly.
            if regions and region:
                region_match = any(
                    r.lower() in region.lower() for r in regions
                )
                if not region_match:
                    continue

            dt = DiscoveredTarget(
                platform=profile["platform"],
                username=profile["username"],
                display_name=profile.get("display_name"),
                profile_url=profile.get("profile_url", f"https://{profile['platform'].value}.com/{profile['username']}"),
                avatar_url=profile.get("avatar_url"),
                bio=bio or None,
                follower_count=profile_followers,
                is_verified=profile.get("is_verified", False),
                gender=inferred_gender,
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
                f"({_format_followers(profile_followers)} followers)"
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
