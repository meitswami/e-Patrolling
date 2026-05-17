"""Repeat offender tracking and accused dossier API."""

import math
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.schemas.common import PaginatedResponse
from auth.middleware import get_current_user
from auth.rbac import require_analyst
from database.connection import get_session
from database.models import AccusedProfile, OffenderStatus, PlatformType, RepeatOffender, User
from osint.lookup import run_osint_lookup
from services.accused_dossier import build_accused_dossier, find_accused_profiles_by_username

router = APIRouter()


class OffenderListItem(BaseModel):
    id: UUID
    accused_id: UUID
    username: str
    platform: PlatformType
    total_offenses: int
    critical_count: int
    priority_score: int
    status: OffenderStatus
    last_offense_at: Optional[datetime]

    model_config = {"from_attributes": True}


@router.get("", response_model=PaginatedResponse[OffenderListItem])
async def list_offenders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[OffenderListItem]:
    Accused = aliased(AccusedProfile)
    base = (
        select(RepeatOffender, Accused.username, Accused.platform)
        .join(Accused, RepeatOffender.accused_id == Accused.id)
        .order_by(RepeatOffender.priority_score.desc())
    )
    count_q = select(func.count()).select_from(RepeatOffender)

    total = await session.scalar(count_q) or 0
    offset = (page - 1) * page_size
    result = await session.execute(base.offset(offset).limit(page_size))

    items: List[OffenderListItem] = []
    for row, username, platform in result.all():
        items.append(
            OffenderListItem(
                id=row.id,
                accused_id=row.accused_id,
                username=username,
                platform=platform,
                total_offenses=row.total_offenses,
                critical_count=row.critical_count,
                priority_score=row.priority_score,
                status=row.status,
                last_offense_at=row.last_offense_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


class AccusedProfileItem(BaseModel):
    id: UUID
    platform: PlatformType
    username: str
    display_name: Optional[str] = None
    profile_url: str
    total_incidents: int
    critical_count: int
    high_count: int
    max_risk_score: int
    status: OffenderStatus
    last_seen_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("/search", response_model=list[AccusedProfileItem])
async def search_accused_profiles(
    username: str = Query(..., min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[AccusedProfileItem]:
    """Find all platform profiles for the same handle (multi-profile accused)."""
    profiles = await find_accused_profiles_by_username(session, username)
    return [AccusedProfileItem.model_validate(p) for p in profiles]


@router.get("/dossier/{username}")
async def get_accused_dossier(
    username: str,
    run_osint: bool = Query(False, description="Refresh OSINT cross-platform lookup"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> dict[str, Any]:
    """Full cross-platform dossier JSON for print UI and PDF export."""
    if run_osint:
        await run_osint_lookup(session, username)
        await session.commit()
    dossier = await build_accused_dossier(session, username)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No accused profiles found for @{username.lstrip('@')}",
        )
    return dossier


@router.post("/dossier/{username}/osint")
async def refresh_accused_osint(
    username: str,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> dict[str, Any]:
    """Run OSINT lookup: match same DP, username, bio across platforms."""
    report = await run_osint_lookup(session, username)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No accused profiles found for @{username.lstrip('@')}",
        )
    await session.commit()
    return report
