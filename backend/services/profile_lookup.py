"""
Profile Lookup Service — fetches profile data from social media platforms.

Primary approach: Uses Playwright browser with saved Instagram session
(the same session the crawler uses) to visit the profile page and extract
data directly from the page/API responses.

Fallback: httpx-based API calls with session cookies.

This service is used by the profile preview API endpoint.
"""

import asyncio
import json
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class ProfileInfo(BaseModel):
    platform: str
    username: str
    profile_url: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    is_verified: bool = False
    is_private: bool = False
    found: bool = False
    error: Optional[str] = None


# ── Cookie helpers ────────────────────────────────────────────

def _get_instagram_cookies() -> dict[str, str]:
    """Load Instagram cookies from the saved Playwright storage state."""
    try:
        from crawlers.instagram.session_manager import InstagramSessionManager
        mgr = InstagramSessionManager()
        if not mgr.has_saved_session():
            return {}
        state = mgr.load_storage_state()
        if not state:
            return {}
        cookies = state.get("cookies", [])
        ig_cookies = {}
        for c in cookies:
            domain = c.get("domain", "")
            if "instagram.com" in domain:
                ig_cookies[c["name"]] = c["value"]
        return ig_cookies
    except Exception as exc:
        logger.debug("Failed to load Instagram cookies: %s", exc)
        return {}


def _cookies_to_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ══════════════════════════════════════════════════════════════
# INSTAGRAM PROFILE LOOKUP — PLAYWRIGHT-BASED (PRIMARY)
# ══════════════════════════════════════════════════════════════

async def lookup_instagram(username: str) -> ProfileInfo:
    """
    Fetch Instagram profile data.

    Strategy order:
    1. httpx API calls with session cookies (fast, gets full data if session works)
    2. Playwright browser (same session as crawler) — most reliable but slower
    3. Returns error with guidance if nothing works
    """
    profile_url = f"https://www.instagram.com/{username}/"

    # Strategy 1: httpx with session cookies (fast — try all API endpoints)
    result = await _httpx_instagram_lookup(username, profile_url)
    if result and result.found and result.followers is not None:
        # Got full data (with stats) — return immediately
        return result

    # Strategy 2: Playwright-based scraping (slower but most reliable)
    pw_result = await _playwright_instagram_lookup(username, profile_url)
    if pw_result and pw_result.found:
        return pw_result

    # Strategy 3: If httpx got partial data (name but no stats), still return it
    if result and result.found:
        return result

    # Nothing worked
    from services import system_settings as app_settings
    if not app_settings.instagram_auth_configured():
        return ProfileInfo(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Connect Instagram in Settings to enable profile preview.",
        )

    return ProfileInfo(
        platform="instagram",
        username=username,
        profile_url=profile_url,
        found=False,
        error="Could not fetch profile (login wall or rate limited)",
    )


async def _playwright_instagram_lookup(
    username: str, profile_url: str
) -> Optional[ProfileInfo]:
    """
    Use Playwright browser (with saved session) to visit profile page
    and intercept the API response that contains full profile data.
    """
    from crawlers.instagram.session_manager import InstagramSessionManager

    session_mgr = InstagramSessionManager()
    if not session_mgr.has_saved_session():
        logger.debug("No Instagram session file for Playwright lookup")
        return None

    storage = session_mgr.load_storage_state()
    if not storage:
        return None

    browser = None
    playwright_instance = None
    try:
        from playwright.async_api import async_playwright

        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            storage_state=storage,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-IN",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        page = await context.new_page()

        # Intercept API responses that contain profile data
        profile_data: dict = {}

        async def handle_response(response):
            nonlocal profile_data
            url = response.url
            try:
                # Catch web_profile_info API response
                if "web_profile_info" in url and response.status == 200:
                    data = await response.json()
                    user = data.get("data", {}).get("user")
                    if user:
                        profile_data["user"] = user
                        logger.debug("Intercepted web_profile_info for @%s", username)
                # Catch graphql user query
                elif "graphql/query" in url and response.status == 200:
                    try:
                        data = await response.json()
                        user = data.get("data", {}).get("user")
                        if user and user.get("username", "").lower() == username.lower():
                            profile_data["user"] = user
                    except Exception:
                        pass
                # Catch __a=1 endpoint
                elif f"/{username}" in url and "__a=1" in url and response.status == 200:
                    data = await response.json()
                    user = (
                        data.get("graphql", {}).get("user")
                        or data.get("data", {}).get("user")
                    )
                    if user:
                        profile_data["user"] = user
            except Exception:
                pass

        page.on("response", handle_response)

        # Navigate to profile page
        try:
            await page.goto(profile_url, wait_until="networkidle", timeout=25000)
            await asyncio.sleep(1.0)  # Extra buffer for late API responses
        except Exception as exc:
            # networkidle might timeout on heavy pages, try with what we have
            logger.debug("Playwright navigation timeout for @%s (continuing): %s", username, exc)
            await asyncio.sleep(1.0)

        # Check if we hit login page
        current_url = page.url
        if "accounts/login" in current_url:
            logger.debug("Instagram login wall hit for @%s", username)
            await page.close()
            await context.close()
            await browser.close()
            await playwright_instance.stop()
            return None

        # If we intercepted API data, use it (most complete)
        if profile_data.get("user"):
            user = profile_data["user"]
            result = _build_ig_profile(username, profile_url, user)
            await page.close()
            await context.close()
            await browser.close()
            await playwright_instance.stop()
            return result

        # Fallback: Make the API call directly from within the page context
        # (this uses the page's own cookies/session which are already authenticated)
        try:
            api_data = await page.evaluate("""async (username) => {
                try {
                    const resp = await fetch(
                        `/api/v1/users/web_profile_info/?username=${username}`,
                        {
                            headers: {
                                'X-IG-App-ID': '936619743392459',
                                'X-Requested-With': 'XMLHttpRequest',
                            },
                            credentials: 'include',
                        }
                    );
                    if (resp.ok) {
                        const data = await resp.json();
                        return data?.data?.user || null;
                    }
                } catch(e) {}
                return null;
            }""", username)
            if api_data:
                result = _build_ig_profile(username, profile_url, api_data)
                await page.close()
                await context.close()
                await browser.close()
                await playwright_instance.stop()
                return result
        except Exception as exc:
            logger.debug("In-page API call failed for @%s: %s", username, exc)

        # Final fallback: Extract data from the page DOM directly
        result = await _extract_profile_from_dom(page, username, profile_url)
        await page.close()
        await context.close()
        await browser.close()
        await playwright_instance.stop()
        return result

    except Exception as exc:
        logger.warning("Playwright profile lookup failed for @%s: %s", username, exc)
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except Exception:
                pass
        return None


async def _extract_profile_from_dom(page, username: str, profile_url: str) -> Optional[ProfileInfo]:
    """
    Extract profile data directly from the Instagram profile page DOM.
    This reads the header section which contains avatar, name, stats, bio.
    """
    try:
        # Try to get profile data from page content via JavaScript evaluation
        data = await page.evaluate("""() => {
            const result = {};

            // Get full name from header
            const headerSection = document.querySelector('header section');
            if (!headerSection) {
                // Try alternative structure
                const mainContent = document.querySelector('main');
                if (!mainContent) return result;
            }

            // Full name (usually in a span inside header)
            const nameEl = document.querySelector('header section span[class*="x1lliihq"]') ||
                          document.querySelector('header h2 + div span') ||
                          document.querySelector('header section > div > div > span');
            if (nameEl) result.full_name = nameEl.textContent.trim();

            // Avatar
            const avatarImg = document.querySelector('header img[alt*="profile"]') ||
                             document.querySelector('header img[data-testid="user-avatar"]') ||
                             document.querySelector('header canvas + img') ||
                             document.querySelector('header section img');
            if (avatarImg) result.avatar_url = avatarImg.src;

            // Stats (followers, following, posts)
            const statElements = document.querySelectorAll('header section ul li') ||
                                document.querySelectorAll('header ul li');
            if (statElements.length >= 3) {
                const getText = (el) => el?.textContent?.trim() || '';
                result.posts_text = getText(statElements[0]);
                result.followers_text = getText(statElements[1]);
                result.following_text = getText(statElements[2]);
            }

            // Alternative: look for spans with specific number patterns
            if (!result.followers_text) {
                const allSpans = document.querySelectorAll('header span');
                const statTexts = [];
                allSpans.forEach(s => {
                    const t = s.textContent.trim();
                    if (t.match(/^[\\d,.]+[KMB]?\\s*(posts?|followers?|following)/i)) {
                        statTexts.push(t);
                    }
                });
                if (statTexts.length >= 3) {
                    result.posts_text = statTexts[0];
                    result.followers_text = statTexts[1];
                    result.following_text = statTexts[2];
                }
            }

            // Bio
            const bioEl = document.querySelector('header section > div > span') ||
                         document.querySelector('header div[class*="biography"]') ||
                         document.querySelector('.-vDIg span');
            if (bioEl && bioEl.textContent.length > 1 && bioEl.textContent.length < 500) {
                result.bio = bioEl.textContent.trim();
            }

            // Verified badge (blue tick SVG)
            const verifiedBadge = document.querySelector('header svg[aria-label="Verified"]') ||
                                 document.querySelector('header span[title="Verified"]') ||
                                 document.querySelector('[data-testid="verified-badge"]');
            result.is_verified = !!verifiedBadge;

            // Private
            const privateText = document.body.textContent;
            result.is_private = privateText.includes('This account is private') ||
                              privateText.includes('This Account is Private');

            // Page title (often has format: "Name (@username)")
            result.page_title = document.title;

            // Try meta tags as additional source
            const ogTitle = document.querySelector('meta[property="og:title"]');
            const ogDesc = document.querySelector('meta[property="og:description"]');
            const ogImage = document.querySelector('meta[property="og:image"]');
            if (ogTitle) result.og_title = ogTitle.content;
            if (ogDesc) result.og_description = ogDesc.content;
            if (ogImage) result.og_image = ogImage.content;

            return result;
        }""")

        if not data:
            return None

        # Parse the extracted data
        full_name = data.get("full_name")
        avatar_url = data.get("avatar_url") or data.get("og_image")
        bio = data.get("bio")
        is_verified = data.get("is_verified", False)
        is_private = data.get("is_private", False)

        # Parse name from og:title if not found in DOM
        if not full_name and data.get("og_title"):
            name_match = re.match(r"^(.+?)\s*\(@", data["og_title"])
            if name_match:
                full_name = name_match.group(1).strip()

        # Parse stats from text
        followers = _parse_stat_text(data.get("followers_text", ""), "followers")
        following = _parse_stat_text(data.get("following_text", ""), "following")
        posts_count = _parse_stat_text(data.get("posts_text", ""), "posts")

        # If we didn't get stats from DOM, try og:description
        if followers is None and data.get("og_description"):
            desc = data["og_description"]
            f_match = re.search(r"([\d,.]+[KMB]?)\s*Followers", desc, re.IGNORECASE)
            fg_match = re.search(r"([\d,.]+[KMB]?)\s*Following", desc, re.IGNORECASE)
            p_match = re.search(r"([\d,.]+[KMB]?)\s*Posts", desc, re.IGNORECASE)
            if f_match:
                followers = _parse_count(f_match.group(1))
            if fg_match:
                following = _parse_count(fg_match.group(1))
            if p_match:
                posts_count = _parse_count(p_match.group(1))

        # Parse bio from og:description if not found
        if not bio and data.get("og_description"):
            desc = data["og_description"]
            # Bio is after the stats portion
            bio_match = re.search(
                r"(?:Posts?|Followers?|Following)\s*[-–—.]\s*(.+?)(?:$)",
                desc, re.DOTALL
            )
            if bio_match:
                bio = bio_match.group(1).strip()
                bio = re.sub(r"\s*(?:See|View)\s+Instagram.*$", "", bio, flags=re.IGNORECASE).strip()
                if len(bio) < 5:
                    bio = None

        if full_name or avatar_url or followers is not None:
            return ProfileInfo(
                platform="instagram",
                username=username,
                profile_url=profile_url,
                full_name=full_name,
                avatar_url=avatar_url,
                bio=bio[:300] if bio else None,
                followers=followers,
                following=following,
                posts_count=posts_count,
                is_verified=is_verified,
                is_private=is_private,
                found=True,
            )
        return None

    except Exception as exc:
        logger.debug("DOM extraction failed for @%s: %s", username, exc)
        return None


def _parse_stat_text(text: str, stat_name: str) -> Optional[int]:
    """Parse a stat text like '1,234 posts' or '10.2K followers' into an integer."""
    if not text:
        return None
    # Extract the number portion
    match = re.search(r"([\d,.]+[KMB]?)", text, re.IGNORECASE)
    if match:
        return _parse_count(match.group(1))
    return None


# ── httpx-based Instagram lookup (fallback) ───────────────────

_IG_APP_ID = "936619743392459"
_COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


async def _httpx_instagram_lookup(username: str, profile_url: str) -> Optional[ProfileInfo]:
    """Fallback: use httpx with session cookies to call Instagram APIs."""
    cookies = _get_instagram_cookies()
    if not cookies or not cookies.get("sessionid"):
        logger.info("Profile preview: no Instagram session cookies available")
        return None

    csrftoken = cookies.get("csrftoken", "")
    logger.info("Profile preview: attempting httpx lookup for @%s (session cookies found)", username)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # Strategy A: web_profile_info (returns full data)
        try:
            api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
            headers = {
                **_COMMON_HEADERS,
                "X-IG-App-ID": _IG_APP_ID,
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": profile_url,
                "Cookie": _cookies_to_header(cookies),
            }
            resp = await client.get(api_url, headers=headers)
            logger.info("Profile preview web_profile_info: status=%d for @%s", resp.status_code, username)
            if resp.status_code == 200:
                data = resp.json()
                user_data = data.get("data", {}).get("user")
                if user_data:
                    logger.info("Profile preview: got full data via web_profile_info for @%s", username)
                    return _build_ig_profile(username, profile_url, user_data)
        except Exception as exc:
            logger.warning("Profile preview web_profile_info failed for @%s: %s", username, exc)

        # Strategy B: topsearch to get user_id, then i.instagram.com mobile API for full info
        try:
            search_url = f"https://www.instagram.com/web/search/topsearch/?context=blended&query={username}&include_reel=true"
            headers = {
                **_COMMON_HEADERS,
                "X-IG-App-ID": _IG_APP_ID,
                "X-CSRFToken": csrftoken,
                "Cookie": _cookies_to_header(cookies),
                "Referer": "https://www.instagram.com/",
            }
            resp = await client.get(search_url, headers=headers)
            logger.info("Profile preview topsearch: status=%d for @%s", resp.status_code, username)
            if resp.status_code == 200:
                data = resp.json()
                users = data.get("users", [])
                for u in users:
                    user_info = u.get("user", {})
                    if user_info.get("username", "").lower() == username.lower():
                        user_id = user_info.get("pk") or user_info.get("pk_id")
                        if user_id:
                            # Get FULL info via i.instagram.com mobile API
                            logger.info("Profile preview: found user_id=%s, fetching full info via mobile API", user_id)
                            full = await _fetch_ig_user_by_id(client, user_id, cookies)
                            if full:
                                logger.info("Profile preview: got full data via mobile API for @%s (followers=%s)", username, full.get("follower_count"))
                                return _build_ig_profile(username, profile_url, full)

                        # Return what search gives us (partial - no stats)
                        logger.info("Profile preview: returning partial data from topsearch for @%s", username)
                        return ProfileInfo(
                            platform="instagram",
                            username=user_info.get("username", username),
                            profile_url=profile_url,
                            full_name=user_info.get("full_name") or None,
                            avatar_url=user_info.get("profile_pic_url") or None,
                            is_verified=user_info.get("is_verified", False),
                            is_private=user_info.get("is_private", False),
                            found=True,
                        )
        except Exception as exc:
            logger.warning("Profile preview topsearch failed for @%s: %s", username, exc)

    return None


async def _fetch_ig_user_by_id(
    client: httpx.AsyncClient, user_id: int | str, cookies: dict[str, str]
) -> Optional[dict]:
    """Fetch full user info via i.instagram.com mobile API."""
    try:
        url = f"https://i.instagram.com/api/v1/users/{user_id}/info/"
        headers = {
            "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 440dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)",
            "X-IG-App-ID": "567067343352427",
            "Cookie": _cookies_to_header(cookies),
        }
        resp = await client.get(url, headers=headers)
        logger.info("Profile preview i.instagram.com: status=%d for user_id=%s", resp.status_code, user_id)
        if resp.status_code == 200:
            data = resp.json()
            user = data.get("user")
            if user:
                logger.info(
                    "Profile preview mobile API success: @%s followers=%s media=%s",
                    user.get("username"), user.get("follower_count"), user.get("media_count"),
                )
            return user
        else:
            logger.warning("Profile preview i.instagram.com returned %d: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Profile preview i.instagram.com failed for id=%s: %s", user_id, exc)
    return None


def _build_ig_profile(username: str, profile_url: str, user_data: dict[str, Any]) -> ProfileInfo:
    """Build ProfileInfo from Instagram user data dict (handles multiple formats)."""
    followers = (
        user_data.get("edge_followed_by", {}).get("count")
        if isinstance(user_data.get("edge_followed_by"), dict)
        else None
    ) or user_data.get("follower_count") or user_data.get("followers_count")

    following = (
        user_data.get("edge_follow", {}).get("count")
        if isinstance(user_data.get("edge_follow"), dict)
        else None
    ) or user_data.get("following_count")

    posts_count = (
        user_data.get("edge_owner_to_timeline_media", {}).get("count")
        if isinstance(user_data.get("edge_owner_to_timeline_media"), dict)
        else None
    ) or user_data.get("media_count")

    avatar = (
        user_data.get("profile_pic_url_hd")
        or (user_data.get("hd_profile_pic_url_info") or {}).get("url")
        or user_data.get("profile_pic_url")
    )

    return ProfileInfo(
        platform="instagram",
        username=user_data.get("username", username),
        profile_url=profile_url,
        full_name=user_data.get("full_name") or None,
        avatar_url=avatar,
        bio=user_data.get("biography") or user_data.get("bio") or None,
        followers=followers,
        following=following,
        posts_count=posts_count,
        is_verified=user_data.get("is_verified", False),
        is_private=user_data.get("is_private", False),
        found=True,
    )


# ══════════════════════════════════════════════════════════════
# TWITTER / X
# ══════════════════════════════════════════════════════════════

async def lookup_twitter(username: str) -> ProfileInfo:
    profile_url = f"https://x.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            api_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
            resp = await client.get(api_url, headers={
                "User-Agent": _COMMON_HEADERS["User-Agent"],
                "Accept": "text/html,*/*",
            })
            if resp.status_code == 200:
                html = resp.text
                name_match = re.search(r'"name"\s*:\s*"([^"]+)"', html)
                avatar_match = re.search(r'"profile_image_url_https"\s*:\s*"([^"]+)"', html)
                desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', html)
                followers_match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
                following_match = re.search(r'"friends_count"\s*:\s*(\d+)', html)
                tweets_match = re.search(r'"statuses_count"\s*:\s*(\d+)', html)
                verified_match = re.search(r'"verified"\s*:\s*(true|false)', html)

                full_name = name_match.group(1) if name_match else None
                avatar_url = avatar_match.group(1).replace("_normal", "_400x400") if avatar_match else None

                if full_name or avatar_url:
                    return ProfileInfo(
                        platform="twitter",
                        username=username,
                        profile_url=profile_url,
                        full_name=full_name,
                        avatar_url=avatar_url,
                        bio=desc_match.group(1) if desc_match else None,
                        followers=int(followers_match.group(1)) if followers_match else None,
                        following=int(following_match.group(1)) if following_match else None,
                        posts_count=int(tweets_match.group(1)) if tweets_match else None,
                        is_verified=bool(verified_match and verified_match.group(1) == "true"),
                        found=True,
                    )

        return ProfileInfo(platform="twitter", username=username, profile_url=profile_url, found=False, error="Could not fetch profile")
    except Exception as exc:
        return ProfileInfo(platform="twitter", username=username, profile_url=profile_url, found=False, error=f"Fetch error: {str(exc)[:100]}")


# ══════════════════════════════════════════════════════════════
# THREADS
# ══════════════════════════════════════════════════════════════

async def lookup_threads(username: str) -> ProfileInfo:
    profile_url = f"https://www.threads.net/@{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={"User-Agent": _COMMON_HEADERS["User-Agent"], "Accept": "text/html,*/*"})
            if resp.status_code == 200:
                html = resp.text
                og_title = _extract_meta(html, "og:title")
                og_desc = _extract_meta(html, "og:description")
                og_image = _extract_meta(html, "og:image")
                full_name = None
                if og_title:
                    m = re.match(r"^(.+?)\s*\(@", og_title)
                    full_name = m.group(1).strip() if m else (og_title if "@" not in og_title else None)
                followers = None
                if og_desc:
                    f_match = re.search(r"([\d,.]+[KMB]?)\s*(?:Followers?|follower)", og_desc, re.IGNORECASE)
                    if f_match:
                        followers = _parse_count(f_match.group(1))
                if full_name or og_image or followers is not None:
                    return ProfileInfo(platform="threads", username=username, profile_url=profile_url, full_name=full_name, avatar_url=og_image, bio=og_desc[:300] if og_desc else None, followers=followers, found=True)
        return ProfileInfo(platform="threads", username=username, profile_url=profile_url, found=False, error="Could not fetch profile")
    except Exception as exc:
        return ProfileInfo(platform="threads", username=username, profile_url=profile_url, found=False, error=f"Fetch error: {str(exc)[:100]}")


# ══════════════════════════════════════════════════════════════
# FACEBOOK
# ══════════════════════════════════════════════════════════════

async def lookup_facebook(username: str) -> ProfileInfo:
    profile_url = f"https://www.facebook.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={"User-Agent": _COMMON_HEADERS["User-Agent"], "Accept": "text/html,*/*"})
            if resp.status_code == 200:
                html = resp.text
                og_title = _extract_meta(html, "og:title")
                og_image = _extract_meta(html, "og:image")
                og_desc = _extract_meta(html, "og:description")
                if og_title or og_image:
                    return ProfileInfo(platform="facebook", username=username, profile_url=profile_url, full_name=og_title, avatar_url=og_image, bio=og_desc[:300] if og_desc else None, found=True)
        return ProfileInfo(platform="facebook", username=username, profile_url=profile_url, found=False, error="Could not fetch (requires login)")
    except Exception as exc:
        return ProfileInfo(platform="facebook", username=username, profile_url=profile_url, found=False, error=f"Fetch error: {str(exc)[:100]}")


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _extract_meta(html: str, property_name: str) -> Optional[str]:
    patterns = [
        rf'<meta\s+(?:property|name)="{re.escape(property_name)}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+(?:property|name)="{re.escape(property_name)}"',
        rf'<meta\s[^>]*(?:property|name)="{re.escape(property_name)}"[^>]*content="([^"]*)"',
        rf'<meta\s[^>]*content="([^"]*)"[^>]*(?:property|name)="{re.escape(property_name)}"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _parse_count(text: str) -> Optional[int]:
    text = text.strip().replace(",", "")
    multiplier = 1
    if text.upper().endswith("K"):
        multiplier = 1000
        text = text[:-1]
    elif text.upper().endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.upper().endswith("B"):
        multiplier = 1_000_000_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return None


# ── Platform dispatcher ───────────────────────────────────────

PLATFORM_LOOKUPS = {
    "instagram": lookup_instagram,
    "twitter": lookup_twitter,
    "threads": lookup_threads,
    "facebook": lookup_facebook,
}


async def lookup_profile(platform: str, username: str) -> ProfileInfo:
    """Main entry point: look up a profile on any supported platform."""
    fetcher = PLATFORM_LOOKUPS.get(platform)
    if not fetcher:
        return ProfileInfo(
            platform=platform,
            username=username,
            profile_url="",
            found=False,
            error=f"Profile preview not supported for {platform}",
        )
    try:
        return await fetcher(username)
    except Exception as exc:
        logger.error("Profile lookup error for @%s on %s: %s", username, platform, exc)
        return ProfileInfo(
            platform=platform,
            username=username,
            profile_url="",
            found=False,
            error=f"Unexpected error: {str(exc)[:100]}",
        )
