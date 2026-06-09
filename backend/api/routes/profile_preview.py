"""Profile preview / lookup endpoint for autocomplete."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session
from database.models import AccusedProfile, TargetAccount
from database.models_discovery import DiscoveredTarget

router = APIRouter()


class ProfilePreviewResult(BaseModel):
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    follower_count: int | None = None
    is_verified: bool = False
    platform: str | None = None
    profile_url: str | None = None
    found: bool = True


@router.get("/profile-preview", response_model=list[ProfilePreviewResult])
async def profile_preview(
    q: str = Query(..., min_length=2, max_length=200),
    platform: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ProfilePreviewResult]:
    """
    Search for profile preview data by username or URL fragment.
    Searches DiscoveredTarget, AccusedProfile, and TargetAccount tables.
    No auth required (used by public form too).
    """
    # Normalize: remove @ prefix and extract username from URL
    query = q.strip().lstrip("@")
    # If it looks like a URL, try to extract username
    if "/" in query:
        parts = query.rstrip("/").split("/")
        query = parts[-1] if parts[-1] else (parts[-2] if len(parts) > 1 else query)

    results: list[ProfilePreviewResult] = []
    seen_usernames: set[str] = set()

    # Search DiscoveredTarget first (has most profile data)
    dt_query = select(DiscoveredTarget).where(
        DiscoveredTarget.username.ilike(f"%{query}%")
    )
    if platform:
        dt_query = dt_query.where(DiscoveredTarget.platform == platform)
    dt_query = dt_query.limit(5)
    dt_result = await session.execute(dt_query)
    for dt in dt_result.scalars().all():
        if dt.username.lower() not in seen_usernames:
            seen_usernames.add(dt.username.lower())
            results.append(ProfilePreviewResult(
                username=dt.username,
                display_name=dt.display_name,
                avatar_url=dt.avatar_url,
                bio=(dt.bio or "")[:150] if dt.bio else None,
                follower_count=dt.follower_count,
                is_verified=dt.is_verified or False,
                platform=dt.platform.value if dt.platform else None,
                profile_url=dt.profile_url,
                found=True,
            ))

    # Search AccusedProfile
    if len(results) < 5:
        ap_query = select(AccusedProfile).where(
            AccusedProfile.username.ilike(f"%{query}%")
        ).limit(5 - len(results))
        ap_result = await session.execute(ap_query)
        for ap in ap_result.scalars().all():
            if ap.username.lower() not in seen_usernames:
                seen_usernames.add(ap.username.lower())
                results.append(ProfilePreviewResult(
                    username=ap.username,
                    display_name=ap.display_name,
                    avatar_url=ap.avatar_url,
                    bio=(ap.bio or "")[:150] if ap.bio else None,
                    follower_count=ap.follower_count,
                    is_verified=ap.is_verified or False,
                    platform=ap.platform.value if ap.platform else None,
                    profile_url=ap.profile_url,
                    found=True,
                ))

    # Also search TargetAccount
    if len(results) < 5:
        ta_query = select(TargetAccount).where(
            TargetAccount.username.ilike(f"%{query}%")
        ).limit(5 - len(results))
        ta_result = await session.execute(ta_query)
        for ta in ta_result.scalars().all():
            if ta.username.lower() not in seen_usernames:
                seen_usernames.add(ta.username.lower())
                results.append(ProfilePreviewResult(
                    username=ta.username,
                    display_name=ta.display_name,
                    avatar_url=ta.avatar_url,
                    bio=None,
                    follower_count=ta.follower_count,
                    is_verified=ta.is_verified or False,
                    platform=ta.platform.value if ta.platform else None,
                    profile_url=ta.profile_url,
                    found=True,
                ))

    return results
