"""
Profile Lookup Service — fetches public profile data from social media platforms.

Uses multiple strategies in order of preference:
1. Instagram session cookies via httpx (fastest, no browser needed)
2. Playwright browser with saved session (most reliable, same as crawler)
3. Public meta tag scraping (fallback, limited data)

This service is used by the profile preview API endpoint.
"""

import asyncio
import json
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel

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


# ── Cookie extraction from saved Playwright session ───────────

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


# ── Instagram profile lookup ──────────────────────────────────

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
    "Sec-Ch-Ua": '"Chromium";v="125", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


async def lookup_instagram(username: str) -> ProfileInfo:
    """Fetch Instagram profile info using saved session cookies."""
    profile_url = f"https://www.instagram.com/{username}/"
    cookies = _get_instagram_cookies()

    if not cookies:
        return ProfileInfo(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error="No Instagram session. Connect Instagram in Settings for profile preview.",
        )

    csrftoken = cookies.get("csrftoken", "")
    sessionid = cookies.get("sessionid", "")
    if not sessionid:
        return ProfileInfo(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Instagram session expired. Reconnect Instagram in Settings.",
        )

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # Strategy 1: web_profile_info endpoint
        try:
            api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
            headers = {
                **_COMMON_HEADERS,
                "X-IG-App-ID": _IG_APP_ID,
                "X-IG-WWW-Claim": cookies.get("x-ig-www-claim", "0"),
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": profile_url,
                "Cookie": _cookies_to_header(cookies),
            }
            resp = await client.get(api_url, headers=headers)
            logger.debug("IG web_profile_info status=%d for @%s", resp.status_code, username)

            if resp.status_code == 200:
                data = resp.json()
                user_data = data.get("data", {}).get("user")
                if user_data:
                    return _build_ig_profile(username, profile_url, user_data)
        except Exception as exc:
            logger.debug("web_profile_info failed for @%s: %s", username, exc)

        # Strategy 2: ?__a=1&__d=dis endpoint
        try:
            url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
            headers = {
                **_COMMON_HEADERS,
                "X-IG-App-ID": _IG_APP_ID,
                "X-CSRFToken": csrftoken,
                "Cookie": _cookies_to_header(cookies),
                "Referer": "https://www.instagram.com/",
            }
            resp = await client.get(url, headers=headers)
            logger.debug("IG __a=1 status=%d for @%s", resp.status_code, username)

            if resp.status_code == 200:
                data = resp.json()
                user_data = (
                    data.get("graphql", {}).get("user")
                    or data.get("data", {}).get("user")
                    or data.get("user")
                )
                if user_data:
                    return _build_ig_profile(username, profile_url, user_data)
        except Exception as exc:
            logger.debug("__a=1 failed for @%s: %s", username, exc)

        # Strategy 3: i.instagram.com mobile API endpoint
        try:
            # First search for the user to get their user_id
            search_url = f"https://www.instagram.com/web/search/topsearch/?context=blended&query={username}&include_reel=true"
            headers = {
                **_COMMON_HEADERS,
                "X-IG-App-ID": _IG_APP_ID,
                "X-CSRFToken": csrftoken,
                "Cookie": _cookies_to_header(cookies),
                "Referer": "https://www.instagram.com/",
            }
            resp = await client.get(search_url, headers=headers)
            logger.debug("IG topsearch status=%d for @%s", resp.status_code, username)

            if resp.status_code == 200:
                data = resp.json()
                users = data.get("users", [])
                for u in users:
                    user_info = u.get("user", {})
                    if user_info.get("username", "").lower() == username.lower():
                        # Found exact match, now try to get full info
                        user_id = user_info.get("pk") or user_info.get("pk_id")
                        if user_id:
                            full_info = await _fetch_ig_user_by_id(client, user_id, cookies)
                            if full_info:
                                return _build_ig_profile(username, profile_url, full_info)

                        # If can't get full info, return what search gives us
                        return ProfileInfo(
                            platform="instagram",
                            username=user_info.get("username", username),
                            profile_url=profile_url,
                            full_name=user_info.get("full_name") or None,
                            avatar_url=user_info.get("profile_pic_url") or None,
                            bio=None,
                            followers=None,
                            following=None,
                            posts_count=None,
                            is_verified=user_info.get("is_verified", False),
                            is_private=user_info.get("is_private", False),
                            found=True,
                        )
        except Exception as exc:
            logger.debug("topsearch failed for @%s: %s", username, exc)

        # Strategy 4: Scrape profile page HTML for OG/meta data
        try:
            headers = {
                "User-Agent": _COMMON_HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Cookie": _cookies_to_header(cookies),
            }
            resp = await client.get(profile_url, headers=headers)
            if resp.status_code == 200:
                html = resp.text
                result = _parse_ig_html(username, profile_url, html)
                if result and result.found:
                    return result
        except Exception as exc:
            logger.debug("HTML scrape failed for @%s: %s", username, exc)

    return ProfileInfo(
        platform="instagram",
        username=username,
        profile_url=profile_url,
        found=False,
        error="Could not fetch profile. Instagram session may be expired — reconnect in Settings.",
    )


async def _fetch_ig_user_by_id(
    client: httpx.AsyncClient, user_id: int | str, cookies: dict[str, str]
) -> Optional[dict]:
    """Fetch full user info by user_id via i.instagram.com mobile API."""
    try:
        url = f"https://i.instagram.com/api/v1/users/{user_id}/info/"
        headers = {
            "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 440dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)",
            "X-IG-App-ID": "567067343352427",  # Android app ID
            "Cookie": _cookies_to_header(cookies),
        }
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("user")
    except Exception as exc:
        logger.debug("i.instagram.com user info failed for id=%s: %s", user_id, exc)
    return None


def _build_ig_profile(username: str, profile_url: str, user_data: dict[str, Any]) -> ProfileInfo:
    """Build ProfileInfo from an Instagram user data dict (handles multiple response formats)."""
    followers = (
        user_data.get("edge_followed_by", {}).get("count")
        if isinstance(user_data.get("edge_followed_by"), dict)
        else user_data.get("follower_count")
        or user_data.get("followers_count")
    )
    following = (
        user_data.get("edge_follow", {}).get("count")
        if isinstance(user_data.get("edge_follow"), dict)
        else user_data.get("following_count")
    )
    posts_count = (
        user_data.get("edge_owner_to_timeline_media", {}).get("count")
        if isinstance(user_data.get("edge_owner_to_timeline_media"), dict)
        else user_data.get("media_count")
    )
    avatar = (
        user_data.get("profile_pic_url_hd")
        or (user_data.get("hd_profile_pic_url_info") or {}).get("url")
        or user_data.get("profile_pic_url")
    )
    bio = user_data.get("biography") or user_data.get("bio") or None

    return ProfileInfo(
        platform="instagram",
        username=user_data.get("username", username),
        profile_url=profile_url,
        full_name=user_data.get("full_name") or None,
        avatar_url=avatar,
        bio=bio,
        followers=followers,
        following=following,
        posts_count=posts_count,
        is_verified=user_data.get("is_verified", False),
        is_private=user_data.get("is_private", False),
        found=True,
    )


def _parse_ig_html(username: str, profile_url: str, html: str) -> Optional[ProfileInfo]:
    """Parse Instagram profile page HTML for OG tags and embedded JSON."""
    # Check if login wall
    if "/accounts/login" in html[:5000] or "loginForm" in html[:5000]:
        return None

    # Try embedded JSON data first
    shared_data = _extract_json_from_html(html)
    if shared_data:
        user_data = _dig_user_from_json(shared_data, username)
        if user_data:
            return _build_ig_profile(username, profile_url, user_data)

    # Fall back to OG meta tags
    og_title = _extract_meta(html, "og:title")
    og_desc = _extract_meta(html, "og:description")
    og_image = _extract_meta(html, "og:image")

    if not og_title and not og_image and not og_desc:
        return None

    full_name = None
    if og_title:
        # Format: "Full Name (@username) • Instagram photos and videos"
        name_match = re.match(r"^(.+?)\s*\(@", og_title)
        if name_match:
            full_name = name_match.group(1).strip()

    followers = None
    following = None
    posts_count = None
    bio = None

    if og_desc:
        f_match = re.search(r"([\d,.]+[KMB]?)\s*Followers", og_desc, re.IGNORECASE)
        fg_match = re.search(r"([\d,.]+[KMB]?)\s*Following", og_desc, re.IGNORECASE)
        p_match = re.search(r"([\d,.]+[KMB]?)\s*Posts", og_desc, re.IGNORECASE)
        if f_match:
            followers = _parse_count(f_match.group(1))
        if fg_match:
            following = _parse_count(fg_match.group(1))
        if p_match:
            posts_count = _parse_count(p_match.group(1))

        # Bio text after stats
        bio_parts = re.split(r"\d+[KMB]?\s*(?:Posts?|Followers?|Following)", og_desc, flags=re.IGNORECASE)
        if len(bio_parts) > 1:
            potential_bio = bio_parts[-1].strip().lstrip(",-–—. ")
            # Remove trailing Instagram boilerplate
            potential_bio = re.sub(
                r"\s*(?:See|View)\s+Instagram.*$", "", potential_bio, flags=re.IGNORECASE
            ).strip()
            if potential_bio and len(potential_bio) > 5:
                bio = potential_bio[:300]

    if full_name or og_image or followers is not None:
        return ProfileInfo(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            full_name=full_name,
            avatar_url=og_image,
            bio=bio,
            followers=followers,
            following=following,
            posts_count=posts_count,
            is_verified=False,
            is_private=False,
            found=True,
        )

    return None


def _extract_json_from_html(html: str) -> Optional[dict]:
    """Extract embedded JSON data from Instagram HTML."""
    # window._sharedData
    match = re.search(r"window\._sharedData\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # window.__additionalDataLoaded
    match = re.search(
        r"window\.__additionalDataLoaded\s*\([^,]+,\s*(\{.+?\})\s*\)\s*;", html, re.DOTALL
    )
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _dig_user_from_json(data: dict, username: str) -> Optional[dict]:
    """Find user object within various JSON structures."""
    try:
        pages = data.get("entry_data", {}).get("ProfilePage", [])
        if pages:
            return pages[0].get("graphql", {}).get("user")
    except (KeyError, IndexError, TypeError):
        pass
    if "user" in data and isinstance(data["user"], dict):
        return data["user"]
    return None


# ── Twitter/X lookup ──────────────────────────────────────────

async def lookup_twitter(username: str) -> ProfileInfo:
    """Fetch X/Twitter profile via syndication endpoint."""
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
                bio = desc_match.group(1) if desc_match else None
                followers = int(followers_match.group(1)) if followers_match else None
                following = int(following_match.group(1)) if following_match else None
                posts_count = int(tweets_match.group(1)) if tweets_match else None
                is_verified = verified_match and verified_match.group(1) == "true"

                if full_name or avatar_url:
                    return ProfileInfo(
                        platform="twitter",
                        username=username,
                        profile_url=profile_url,
                        full_name=full_name,
                        avatar_url=avatar_url,
                        bio=bio,
                        followers=followers,
                        following=following,
                        posts_count=posts_count,
                        is_verified=bool(is_verified),
                        found=True,
                    )

        return ProfileInfo(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile",
        )
    except Exception as exc:
        return ProfileInfo(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Threads lookup ────────────────────────────────────────────

async def lookup_threads(username: str) -> ProfileInfo:
    """Fetch Threads profile via public page meta tags."""
    profile_url = f"https://www.threads.net/@{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={
                "User-Agent": _COMMON_HEADERS["User-Agent"],
                "Accept": "text/html,*/*",
            })
            if resp.status_code == 200:
                html = resp.text
                og_title = _extract_meta(html, "og:title")
                og_desc = _extract_meta(html, "og:description")
                og_image = _extract_meta(html, "og:image")

                full_name = None
                if og_title:
                    name_match = re.match(r"^(.+?)\s*\(@", og_title)
                    if name_match:
                        full_name = name_match.group(1).strip()
                    elif og_title and "@" not in og_title:
                        full_name = og_title.strip()

                followers = None
                if og_desc:
                    f_match = re.search(r"([\d,.]+[KMB]?)\s*(?:Followers|follower)", og_desc, re.IGNORECASE)
                    if f_match:
                        followers = _parse_count(f_match.group(1))

                if full_name or og_image or followers is not None:
                    return ProfileInfo(
                        platform="threads",
                        username=username,
                        profile_url=profile_url,
                        full_name=full_name,
                        avatar_url=og_image,
                        bio=og_desc[:300] if og_desc else None,
                        followers=followers,
                        found=True,
                    )

        return ProfileInfo(
            platform="threads",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile",
        )
    except Exception as exc:
        return ProfileInfo(
            platform="threads",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Facebook lookup ───────────────────────────────────────────

async def lookup_facebook(username: str) -> ProfileInfo:
    """Fetch Facebook profile from public page."""
    profile_url = f"https://www.facebook.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={
                "User-Agent": _COMMON_HEADERS["User-Agent"],
                "Accept": "text/html,*/*",
            })
            if resp.status_code == 200:
                html = resp.text
                og_title = _extract_meta(html, "og:title")
                og_desc = _extract_meta(html, "og:description")
                og_image = _extract_meta(html, "og:image")

                if og_title or og_image:
                    return ProfileInfo(
                        platform="facebook",
                        username=username,
                        profile_url=profile_url,
                        full_name=og_title,
                        avatar_url=og_image,
                        bio=og_desc[:300] if og_desc else None,
                        found=True,
                    )

        return ProfileInfo(
            platform="facebook",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile (requires login)",
        )
    except Exception as exc:
        return ProfileInfo(
            platform="facebook",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Helpers ──────────────────────────────────────────────────

def _extract_meta(html: str, property_name: str) -> Optional[str]:
    """Extract content from an OG/meta tag (handles various attribute orderings)."""
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
    """Parse human-readable count like '1.2M', '10K', '1,234'."""
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
    profile_url = ""
    if platform == "instagram":
        profile_url = f"https://www.instagram.com/{username}/"
    elif platform == "twitter":
        profile_url = f"https://x.com/{username}"
    elif platform == "threads":
        profile_url = f"https://www.threads.net/@{username}"
    elif platform == "facebook":
        profile_url = f"https://www.facebook.com/{username}"

    fetcher = PLATFORM_LOOKUPS.get(platform)
    if not fetcher:
        return ProfileInfo(
            platform=platform,
            username=username,
            profile_url=profile_url,
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
            profile_url=profile_url,
            found=False,
            error=f"Unexpected error: {str(exc)[:100]}",
        )
