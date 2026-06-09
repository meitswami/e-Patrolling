"""
Profile Preview API — public endpoint for AJAX profile lookup.

Returns basic public profile info (avatar, name, followers, following, posts, bio, verified)
for a given username or profile URL.
"""

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from services.profile_lookup import ProfileInfo, lookup_profile
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
    Used by the frontend for instant AJAX profile preview dropdown.

    Requires an active Instagram session (Settings → Connect Instagram)
    for full profile data. Without it, limited public data may be returned.
    """
    text = q.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        platform_enum, username, profile_url = parse_profile_input(text)
        platform = platform_enum.value
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = await lookup_profile(platform, username)

    # Ensure profile_url is the normalized one from parse_profile_input
    return ProfilePreviewResponse(
        platform=result.platform,
        username=result.username,
        profile_url=profile_url,
        full_name=result.full_name,
        avatar_url=result.avatar_url,
        bio=result.bio,
        followers=result.followers,
        following=result.following,
        posts_count=result.posts_count,
        is_verified=result.is_verified,
        is_private=result.is_private,
        found=result.found,
        error=result.error,
    )


# ── Image Proxy ────────────────────────────────────────────────
# Instagram CDN images don't have CORS headers, so the browser blocks
# them when loaded cross-origin. This proxy fetches the image server-side
# and serves it from our own domain with proper headers.

_ALLOWED_IMAGE_HOSTS = {
    "scontent.cdninstagram.com",
    "instagram.com",
    "cdninstagram.com",
    "fbcdn.net",
    "twimg.com",
    "pbs.twimg.com",
    "abs.twimg.com",
    "threads.net",
}


def _is_allowed_image_host(url: str) -> bool:
    """Check if the image URL is from an allowed CDN host."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return any(allowed in host for allowed in _ALLOWED_IMAGE_HOSTS)
    except Exception:
        return False


@router.get("/proxy-image")
async def proxy_image(
    url: str = Query(..., min_length=10, max_length=2000, description="Image URL to proxy"),
):
    """
    Proxy an image from Instagram/Twitter CDN to avoid CORS issues.
    Only allows images from known social media CDN hosts.
    """
    if not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Only HTTPS URLs are allowed")

    if not _is_allowed_image_host(url):
        raise HTTPException(status_code=403, detail="Image host not allowed")

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "image/*,*/*",
                "Referer": "https://www.instagram.com/",
            })
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch image")

            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                },
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timed out")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to proxy image")
