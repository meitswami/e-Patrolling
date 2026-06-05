"""
Profile Preview API — public endpoint for AJAX profile lookup.

Returns basic public profile info (avatar, name, followers, following, posts, bio, verified)
for a given username or profile URL.
"""

from fastapi import APIRouter, HTTPException, Query
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
