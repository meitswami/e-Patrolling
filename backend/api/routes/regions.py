"""Regional intelligence API."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from database.connection import get_session
from database.models import AccusedProfile, TargetAccount, User
from pydantic import BaseModel

router = APIRouter()


class RegionSummary(BaseModel):
    region: str
    target_count: int
    accused_count: int
    avg_confidence: float


@router.get("/summary", response_model=list[RegionSummary])
async def regions_summary(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[RegionSummary]:
    """Aggregate targets and accused by inferred region."""
    target_rows = await session.execute(
        select(
            TargetAccount.inferred_region,
            func.count(),
            func.avg(TargetAccount.region_confidence),
        )
        .where(TargetAccount.inferred_region.isnot(None))
        .group_by(TargetAccount.inferred_region)
    )
    accused_rows = await session.execute(
        select(AccusedProfile.inferred_region, func.count())
        .where(AccusedProfile.inferred_region.isnot(None))
        .group_by(AccusedProfile.inferred_region)
    )

    accused_map = {r: c for r, c in accused_rows.all()}
    summaries: list[RegionSummary] = []

    for region, t_count, avg_conf in target_rows.all():
        summaries.append(
            RegionSummary(
                region=region or "Unknown",
                target_count=t_count,
                accused_count=accused_map.get(region, 0),
                avg_confidence=float(avg_conf or 0),
            )
        )

    for region, a_count in accused_map.items():
        if not any(s.region == region for s in summaries):
            summaries.append(
                RegionSummary(
                    region=region,
                    target_count=0,
                    accused_count=a_count,
                    avg_confidence=0.0,
                )
            )

    summaries.sort(key=lambda x: x.target_count + x.accused_count, reverse=True)
    return summaries
