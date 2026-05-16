"""Repeat offender tracking API."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.schemas.common import PaginatedResponse
from auth.middleware import get_current_user
from database.connection import get_session
from database.models import AccusedProfile, RepeatOffender, User
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from database.models import OffenderStatus, PlatformType

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
