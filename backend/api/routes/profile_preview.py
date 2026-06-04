"""
Profile Preview API — public endpoint for AJAX profile lookup.

Fetches basic profile info (avatar, display name, followers, following, posts, bio, verified)
from social media platforms given a username or profile URL.

Uses the saved Instagram session cookies (if available) to make authenticated requests,
falling back to public scraping methods.
"""

import json
import re
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from utils.profile_parse import parse_profile_input

router = APIRouter()


class ProfilePreviewResponse(BaseModel):
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


# ── Common headers ─────────────────────────────────────────────

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Ch-Ua": '"Chromium";v="125", "Google Chrome";v="125", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

_IG_APP_ID = "936619743392459"


# ── Instagram session cookie loader ───────────────────────────

def _load_instagram_cookies() -> dict[str, str]:
    """Load Instagram cookies from the saved Playwright session state."""
    try:
        from crawlers.instagram.session_manager import InstagramSessionManager
        mgr = InstagramSessionManager()
        state = mgr.load_storage_state()
        if not state:
            return {}
        cookies = state.get("cookies", [])
        # Extract cookies for instagram.com
        ig_cookies = {}
        for c in cookies:
            domain = c.get("domain", "")
            if "instagram.com" in domain:
                ig_cookies[c["name"]] = c["value"]
        return ig_cookies
    except Exception:
        return {}


def _cookies_to_header(cookies: dict[str, str]) -> str:
    """Convert cookie dict to Cookie header string."""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ── Instagram profile fetch (multiple strategies) ─────────────

async def _fetch_instagram_profile(username: str) -> ProfilePreviewResponse:
    """
    Fetch Instagram profile using multiple strategies:
    1. Authenticated web_profile_info API (using saved session cookies)
    2. i.instagram.com mobile API (using saved session cookies)
    3. Public HTML page meta tag scraping (fallback)
    """
    profile_url = f"https://www.instagram.com/{username}/"
    cookies = _load_instagram_cookies()

    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=True
    ) as client:

        # Strategy 1: web_profile_info API with session cookies
        if cookies:
            result = await _ig_web_profile_info(client, username, profile_url, cookies)
            if result and result.found:
                return result

        # Strategy 2: i.instagram.com API (mobile API) with session cookies
        if cookies:
            result = await _ig_mobile_api(client, username, profile_url, cookies)
            if result and result.found:
                return result

        # Strategy 3: GraphQL query with session cookies
        if cookies:
            result = await _ig_graphql_query(client, username, profile_url, cookies)
            if result and result.found:
                return result

        # Strategy 4: Public HTML page meta tags (no auth needed but limited)
        result = await _ig_html_meta_scrape(client, username, profile_url, cookies)
        if result and result.found:
            return result

        # Nothing worked
        error_msg = (
            "Could not fetch profile. "
            + ("Instagram session may be expired — reconnect in Settings." if cookies else "No Instagram session configured — connect in Settings for profile preview.")
        )
        return ProfilePreviewResponse(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error=error_msg,
        )


async def _ig_web_profile_info(
    client: httpx.AsyncClient,
    username: str,
    profile_url: str,
    cookies: dict[str, str],
) -> Optional[ProfilePreviewResponse]:
    """Strategy 1: Instagram web_profile_info REST API."""
    try:
        api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {
            **_BROWSER_HEADERS,
            "X-IG-App-ID": _IG_APP_ID,
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": cookies.get("csrftoken", ""),
            "Referer": profile_url,
            "Cookie": _cookies_to_header(cookies),
        }
        resp = await client.get(api_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            user_data = data.get("data", {}).get("user")
            if user_data:
                return _build_ig_response(username, profile_url, user_data)
    except Exception:
        pass
    return None


async def _ig_mobile_api(
    client: httpx.AsyncClient,
    username: str,
    profile_url: str,
    cookies: dict[str, str],
) -> Optional[ProfilePreviewResponse]:
    """Strategy 2: i.instagram.com mobile API."""
    try:
        # First get user ID from username search
        search_url = f"https://www.instagram.com/web/search/topsearch/?query={username}"
        headers = {
            **_BROWSER_HEADERS,
            "X-IG-App-ID": _IG_APP_ID,
            "X-CSRFToken": cookies.get("csrftoken", ""),
            "Cookie": _cookies_to_header(cookies),
            "Referer": "https://www.instagram.com/",
        }
        resp = await client.get(search_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("users", [])
            for u in users:
                user_info = u.get("user", {})
                if user_info.get("username", "").lower() == username.lower():
                    return ProfilePreviewResponse(
                        platform="instagram",
                        username=user_info.get("username", username),
                        profile_url=profile_url,
                        full_name=user_info.get("full_name") or None,
                        avatar_url=user_info.get("profile_pic_url") or None,
                        bio=None,  # Not in search results
                        followers=None,  # Not in search results
                        following=None,
                        posts_count=None,
                        is_verified=user_info.get("is_verified", False),
                        is_private=user_info.get("is_private", False),
                        found=True,
                    )
            # If found in search (first result) but username doesn't exactly match
            if users:
                user_info = users[0].get("user", {})
                if user_info.get("username", "").lower() == username.lower():
                    return ProfilePreviewResponse(
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
    except Exception:
        pass
    return None


async def _ig_graphql_query(
    client: httpx.AsyncClient,
    username: str,
    profile_url: str,
    cookies: dict[str, str],
) -> Optional[ProfilePreviewResponse]:
    """Strategy 3: Instagram GraphQL user query."""
    try:
        # Use the user info endpoint
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {
            **_BROWSER_HEADERS,
            "X-IG-App-ID": _IG_APP_ID,
            "X-CSRFToken": cookies.get("csrftoken", ""),
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": _cookies_to_header(cookies),
            "Referer": profile_url,
        }
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            try:
                data = resp.json()
                # Response format: {"graphql": {"user": {...}}} or {"data": {"user": {...}}}
                user_data = (
                    data.get("graphql", {}).get("user")
                    or data.get("data", {}).get("user")
                    or data.get("user")
                )
                if user_data:
                    return _build_ig_response(username, profile_url, user_data)
            except (json.JSONDecodeError, ValueError):
                pass
    except Exception:
        pass
    return None


async def _ig_html_meta_scrape(
    client: httpx.AsyncClient,
    username: str,
    profile_url: str,
    cookies: dict[str, str],
) -> Optional[ProfilePreviewResponse]:
    """Strategy 4: Scrape Instagram profile HTML page meta/OG tags."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        if cookies:
            headers["Cookie"] = _cookies_to_header(cookies)

        resp = await client.get(profile_url, headers=headers)
        if resp.status_code != 200:
            return None

        html = resp.text

        # Check if we hit the login page
        if "accounts/login" in resp.url.path if hasattr(resp, 'url') else False:
            return None

        # Extract OG meta tags
        og_title = _extract_meta(html, "og:title")
        og_desc = _extract_meta(html, "og:description")
        og_image = _extract_meta(html, "og:image")

        # Also try to extract from embedded JSON (SharedData or additional_data)
        json_data = _extract_shared_data(html)
        if json_data:
            user_data = _dig_user_from_shared_data(json_data, username)
            if user_data:
                return _build_ig_response(username, profile_url, user_data)

        # Parse from OG tags
        full_name = None
        if og_title:
            # Format: "Full Name (@username) • Instagram photos and videos"
            name_match = re.match(r"^(.+?)\s*\(@", og_title)
            if name_match:
                full_name = name_match.group(1).strip()
            elif "instagram" not in (og_title or "").lower():
                full_name = og_title.split("(")[0].strip() if "(" in og_title else None

        followers = None
        following = None
        posts_count = None
        bio = None

        if og_desc:
            # Format: "1.2M Followers, 200 Following, 500 Posts - See Instagram..."
            f_match = re.search(r"([\d,.]+[KMB]?)\s*Followers", og_desc, re.IGNORECASE)
            fg_match = re.search(r"([\d,.]+[KMB]?)\s*Following", og_desc, re.IGNORECASE)
            p_match = re.search(r"([\d,.]+[KMB]?)\s*Posts", og_desc, re.IGNORECASE)
            if f_match:
                followers = _parse_count(f_match.group(1))
            if fg_match:
                following = _parse_count(fg_match.group(1))
            if p_match:
                posts_count = _parse_count(p_match.group(1))

            # Bio: text after the stats
            bio_match = re.search(
                r"Posts?\s*[-–—:\.]\s*(.+?)(?:\s*$)", og_desc, re.DOTALL
            )
            if bio_match:
                bio = bio_match.group(1).strip()
                # Remove "See Instagram photos and videos..." suffix
                bio = re.sub(
                    r"\s*See Instagram photos and videos.*$", "", bio, flags=re.IGNORECASE
                ).strip()
                if bio:
                    bio = bio[:300]
                else:
                    bio = None

        if full_name or og_image or followers is not None:
            return ProfilePreviewResponse(
                platform="instagram",
                username=username,
                profile_url=profile_url,
                full_name=full_name,
                avatar_url=og_image,
                bio=bio,
                followers=followers,
                following=following,
                posts_count=posts_count,
                is_verified=False,  # Can't determine from meta alone
                is_private=False,
                found=True,
            )
    except Exception:
        pass
    return None


def _build_ig_response(
    username: str, profile_url: str, user_data: dict[str, Any]
) -> ProfilePreviewResponse:
    """Build a ProfilePreviewResponse from Instagram user data dict."""
    # Handle different response formats
    followers = (
        user_data.get("edge_followed_by", {}).get("count")
        or user_data.get("follower_count")
        or user_data.get("followers_count")
    )
    following = (
        user_data.get("edge_follow", {}).get("count")
        or user_data.get("following_count")
    )
    posts_count = (
        user_data.get("edge_owner_to_timeline_media", {}).get("count")
        or user_data.get("media_count")
    )
    avatar = (
        user_data.get("profile_pic_url_hd")
        or user_data.get("hd_profile_pic_url_info", {}).get("url")
        or user_data.get("profile_pic_url")
    )

    return ProfilePreviewResponse(
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


def _extract_shared_data(html: str) -> Optional[dict]:
    """Extract window._sharedData or window.__additionalDataLoaded from Instagram page HTML."""
    # Try _sharedData
    match = re.search(r"window\._sharedData\s*=\s*(\{.+?\});\s*</script>", html, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try __additionalDataLoaded
    match = re.search(
        r"window\.__additionalDataLoaded\s*\([^,]+,\s*(\{.+?\})\s*\)\s*;", html, re.DOTALL
    )
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try require("ServerJS").handle with profile data
    match = re.search(r'"user":\s*(\{"[^}]*"username"[^}]*\})', html)
    if match:
        try:
            return {"entry_data": {"ProfilePage": [{"graphql": {"user": json.loads(match.group(1))}}]}}
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _dig_user_from_shared_data(data: dict, username: str) -> Optional[dict]:
    """Find user object within sharedData structure."""
    # Standard path: entry_data.ProfilePage[0].graphql.user
    try:
        pages = data.get("entry_data", {}).get("ProfilePage", [])
        if pages:
            return pages[0].get("graphql", {}).get("user")
    except (KeyError, IndexError, TypeError):
        pass

    # Alternative path: data.user
    if "user" in data and isinstance(data["user"], dict):
        return data["user"]

    return None


# ── Twitter/X profile fetch ────────────────────────────────────

async def _fetch_twitter_profile(username: str) -> ProfilePreviewResponse:
    """Fetch X/Twitter profile via syndication endpoint (public, no API key)."""
    profile_url = f"https://x.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            # Twitter syndication API (public)
            api_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
            resp = await client.get(api_url, headers={
                "User-Agent": _BROWSER_HEADERS["User-Agent"],
                "Accept": "text/html,*/*",
            })

            if resp.status_code == 200:
                html = resp.text
                # Extract from embedded JSON/HTML
                name_match = re.search(r'"name"\s*:\s*"([^"]+)"', html)
                avatar_match = re.search(r'"profile_image_url_https"\s*:\s*"([^"]+)"', html)
                desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', html)
                followers_match = re.search(r'"followers_count"\s*:\s*(\d+)', html)
                following_match = re.search(r'"friends_count"\s*:\s*(\d+)', html)
                tweets_match = re.search(r'"statuses_count"\s*:\s*(\d+)', html)
                verified_match = re.search(r'"verified"\s*:\s*(true|false)', html)

                full_name = name_match.group(1) if name_match else None
                avatar_url = (
                    avatar_match.group(1).replace("_normal", "_400x400")
                    if avatar_match
                    else None
                )
                bio = desc_match.group(1) if desc_match else None
                followers = int(followers_match.group(1)) if followers_match else None
                following = int(following_match.group(1)) if following_match else None
                posts_count = int(tweets_match.group(1)) if tweets_match else None
                is_verified = verified_match and verified_match.group(1) == "true"

                if full_name or avatar_url:
                    return ProfilePreviewResponse(
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

        return ProfilePreviewResponse(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile",
        )
    except httpx.TimeoutException:
        return ProfilePreviewResponse(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Request timed out",
        )
    except Exception as exc:
        return ProfilePreviewResponse(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Threads profile fetch ─────────────────────────────────────

async def _fetch_threads_profile(username: str) -> ProfilePreviewResponse:
    """Fetch Threads profile from public page meta tags."""
    profile_url = f"https://www.threads.net/@{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={
                "User-Agent": _BROWSER_HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml,*/*",
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
                    f_match = re.search(
                        r"([\d,.]+[KMB]?)\s*(?:Followers|follower)",
                        og_desc,
                        re.IGNORECASE,
                    )
                    if f_match:
                        followers = _parse_count(f_match.group(1))

                if full_name or og_image or followers is not None:
                    return ProfilePreviewResponse(
                        platform="threads",
                        username=username,
                        profile_url=profile_url,
                        full_name=full_name,
                        avatar_url=og_image,
                        bio=og_desc[:300] if og_desc else None,
                        followers=followers,
                        found=True,
                    )

        return ProfilePreviewResponse(
            platform="threads",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile",
        )
    except Exception as exc:
        return ProfilePreviewResponse(
            platform="threads",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Facebook profile fetch ────────────────────────────────────

async def _fetch_facebook_profile(username: str) -> ProfilePreviewResponse:
    """Fetch Facebook profile from public page (limited due to FB restrictions)."""
    profile_url = f"https://www.facebook.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers={
                "User-Agent": _BROWSER_HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml,*/*",
            })
            if resp.status_code == 200:
                html = resp.text
                og_title = _extract_meta(html, "og:title")
                og_desc = _extract_meta(html, "og:description")
                og_image = _extract_meta(html, "og:image")

                if og_title or og_image:
                    return ProfilePreviewResponse(
                        platform="facebook",
                        username=username,
                        profile_url=profile_url,
                        full_name=og_title,
                        avatar_url=og_image,
                        bio=og_desc[:300] if og_desc else None,
                        found=True,
                    )

        return ProfilePreviewResponse(
            platform="facebook",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Could not fetch profile (requires login)",
        )
    except Exception as exc:
        return ProfilePreviewResponse(
            platform="facebook",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


# ── Helpers ──────────────────────────────────────────────────────

def _extract_meta(html: str, property_name: str) -> Optional[str]:
    """Extract content from an OG meta tag."""
    # property="..." content="..."
    pattern = rf'<meta\s+(?:property|name)="{re.escape(property_name)}"\s+content="([^"]*)"'
    match = re.search(pattern, html, re.IGNORECASE)
    if not match:
        # content="..." property="..."
        pattern2 = rf'<meta\s+content="([^"]*)"\s+(?:property|name)="{re.escape(property_name)}"'
        match = re.search(pattern2, html, re.IGNORECASE)
    if not match:
        # Handle multi-attribute with spaces/other attributes in between
        pattern3 = (
            rf'<meta\s[^>]*(?:property|name)="{re.escape(property_name)}"[^>]*content="([^"]*)"'
        )
        match = re.search(pattern3, html, re.IGNORECASE)
    if not match:
        pattern4 = (
            rf'<meta\s[^>]*content="([^"]*)"[^>]*(?:property|name)="{re.escape(property_name)}"'
        )
        match = re.search(pattern4, html, re.IGNORECASE)
    return match.group(1) if match else None


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


_PLATFORM_FETCHERS = {
    "instagram": _fetch_instagram_profile,
    "twitter": _fetch_twitter_profile,
    "threads": _fetch_threads_profile,
    "facebook": _fetch_facebook_profile,
}


# ── Route ──────────────────────────────────────────────────────

@router.get("/profile-preview", response_model=ProfilePreviewResponse)
async def profile_preview(
    q: str = Query(
        ...,
        min_length=1,
        max_length=500,
        description="Username (e.g. @username) or full profile URL",
    ),
) -> ProfilePreviewResponse:
    """
    Lookup a social media profile and return basic public info.
    Used by the frontend for instant AJAX profile preview in the form inputs.

    Uses saved Instagram session cookies (if available) for authenticated requests.
    Falls back to public scraping (OG meta tags) when no session is available.
    """
    text = q.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        platform_enum, username, profile_url = parse_profile_input(text)
        platform = platform_enum.value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    fetcher = _PLATFORM_FETCHERS.get(platform)
    if not fetcher:
        return ProfilePreviewResponse(
            platform=platform,
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Profile preview not supported for {platform}",
        )

    try:
        result = await fetcher(username)
        result.profile_url = profile_url
        return result
    except Exception as exc:
        return ProfilePreviewResponse(
            platform=platform,
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Unexpected error: {str(exc)[:100]}",
        )
