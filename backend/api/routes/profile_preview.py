"""
Profile Preview API — public endpoint for AJAX profile lookup.

Fetches basic profile info (avatar, display name, followers, following, posts, bio, verified)
from social media platforms given a username or profile URL.
"""

import asyncio
import re
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, status
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


# ── Instagram public profile scraper (no auth needed) ──────────

_IG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "navigate",
}


async def _fetch_instagram_profile(username: str) -> ProfilePreviewResponse:
    """Fetch Instagram profile via the public web profile info API."""
    profile_url = f"https://www.instagram.com/{username}/"
    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=True, headers=_IG_HEADERS
        ) as client:
            # Try the web_profile_info GraphQL endpoint (works without login for public profiles)
            api_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
            headers = {
                **_IG_HEADERS,
                "X-IG-App-ID": "936619743392459",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": profile_url,
            }
            resp = await client.get(api_url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                user_data = data.get("data", {}).get("user", {})
                if user_data:
                    return ProfilePreviewResponse(
                        platform="instagram",
                        username=username,
                        profile_url=profile_url,
                        full_name=user_data.get("full_name") or None,
                        avatar_url=user_data.get("profile_pic_url_hd")
                        or user_data.get("profile_pic_url"),
                        bio=user_data.get("biography") or None,
                        followers=user_data.get("edge_followed_by", {}).get("count"),
                        following=user_data.get("edge_follow", {}).get("count"),
                        posts_count=user_data.get("edge_owner_to_timeline_media", {}).get(
                            "count"
                        ),
                        is_verified=user_data.get("is_verified", False),
                        is_private=user_data.get("is_private", False),
                        found=True,
                    )

            # Fallback: scrape meta tags from HTML profile page
            html_resp = await client.get(profile_url)
            if html_resp.status_code == 200:
                html = html_resp.text
                # Try to extract from meta tags
                og_title = _extract_meta(html, "og:title")
                og_desc = _extract_meta(html, "og:description")
                og_image = _extract_meta(html, "og:image")

                full_name = None
                if og_title:
                    # Format: "Full Name (@username) ..." or just "@username"
                    name_match = re.match(r"^(.+?)\s*\(@", og_title)
                    if name_match:
                        full_name = name_match.group(1).strip()

                followers = None
                following = None
                posts_count = None
                if og_desc:
                    # Format: "1.2M Followers, 200 Following, 500 Posts - ..."
                    f_match = re.search(r"([\d,.]+[KMB]?)\s*Followers", og_desc, re.IGNORECASE)
                    fg_match = re.search(r"([\d,.]+[KMB]?)\s*Following", og_desc, re.IGNORECASE)
                    p_match = re.search(r"([\d,.]+[KMB]?)\s*Posts", og_desc, re.IGNORECASE)
                    if f_match:
                        followers = _parse_count(f_match.group(1))
                    if fg_match:
                        following = _parse_count(fg_match.group(1))
                    if p_match:
                        posts_count = _parse_count(p_match.group(1))

                bio = None
                if og_desc:
                    # Bio is usually after the stats line
                    bio_match = re.search(
                        r"Posts?\s*[-–—]\s*(.+)", og_desc, re.DOTALL
                    )
                    if bio_match:
                        bio = bio_match.group(1).strip()[:300]

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

            # Profile not found or login wall
            if resp.status_code == 404 or html_resp.status_code == 404:
                return ProfilePreviewResponse(
                    platform="instagram",
                    username=username,
                    profile_url=profile_url,
                    found=False,
                    error="Profile not found",
                )

            return ProfilePreviewResponse(
                platform="instagram",
                username=username,
                profile_url=profile_url,
                found=False,
                error="Could not fetch profile (login wall or rate limited)",
            )

    except httpx.TimeoutException:
        return ProfilePreviewResponse(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error="Request timed out",
        )
    except Exception as exc:
        return ProfilePreviewResponse(
            platform="instagram",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


async def _fetch_twitter_profile(username: str) -> ProfilePreviewResponse:
    """Fetch X/Twitter profile via syndication endpoint (public, no API key)."""
    profile_url = f"https://x.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Twitter syndication API (public)
            api_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
            resp = await client.get(api_url, headers=_IG_HEADERS)

            if resp.status_code == 200:
                html = resp.text
                # Extract from embedded JSON/HTML
                name_match = re.search(
                    r'"name"\s*:\s*"([^"]+)"', html
                )
                avatar_match = re.search(
                    r'"profile_image_url_https"\s*:\s*"([^"]+)"', html
                )
                desc_match = re.search(
                    r'"description"\s*:\s*"([^"]*)"', html
                )
                followers_match = re.search(
                    r'"followers_count"\s*:\s*(\d+)', html
                )
                following_match = re.search(
                    r'"friends_count"\s*:\s*(\d+)', html
                )
                tweets_match = re.search(
                    r'"statuses_count"\s*:\s*(\d+)', html
                )
                verified_match = re.search(
                    r'"verified"\s*:\s*(true|false)', html
                )

                full_name = name_match.group(1) if name_match else None
                avatar_url = avatar_match.group(1).replace("_normal", "_400x400") if avatar_match else None
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
    except Exception as exc:
        return ProfilePreviewResponse(
            platform="twitter",
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Fetch error: {str(exc)[:100]}",
        )


async def _fetch_threads_profile(username: str) -> ProfilePreviewResponse:
    """Fetch Threads profile from public page meta tags."""
    profile_url = f"https://www.threads.net/@{username}"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers=_IG_HEADERS)
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


async def _fetch_facebook_profile(username: str) -> ProfilePreviewResponse:
    """Fetch Facebook profile from public page (limited due to FB restrictions)."""
    profile_url = f"https://www.facebook.com/{username}"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(profile_url, headers=_IG_HEADERS)
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
    pattern = rf'<meta\s+(?:property|name)="{re.escape(property_name)}"\s+content="([^"]*)"'
    match = re.search(pattern, html, re.IGNORECASE)
    if not match:
        # Try reversed attribute order
        pattern2 = rf'<meta\s+content="([^"]*)"\s+(?:property|name)="{re.escape(property_name)}"'
        match = re.search(pattern2, html, re.IGNORECASE)
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
        # Unsupported platform — return minimal info
        return ProfilePreviewResponse(
            platform=platform,
            username=username,
            profile_url=profile_url,
            found=False,
            error=f"Profile preview not supported for {platform}",
        )

    result = await fetcher(username)
    # Ensure URL matches the normalized one
    result.profile_url = profile_url
    return result
