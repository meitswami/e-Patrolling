"""Regional intelligence API."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from auth.middleware import get_current_user
from database.connection import get_session
from database.models import AccusedProfile, EvidenceReport, SeverityLevel, TargetAccount, User

router = APIRouter()


class RegionSummary(BaseModel):
    region: str
    target_count: int
    accused_count: int
    evidence_count: int = 0
    critical_evidence: int = 0
    avg_confidence: float


class RegionDetail(BaseModel):
    region: str
    targets: list[dict]
    accused: list[dict]
    evidence_by_severity: dict[str, int]


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

    evidence_rows = await session.execute(
        select(
            TargetAccount.inferred_region,
            EvidenceReport.severity_level,
            func.count(),
        )
        .join(TargetAccount, EvidenceReport.target_id == TargetAccount.id)
        .where(TargetAccount.inferred_region.isnot(None))
        .group_by(TargetAccount.inferred_region, EvidenceReport.severity_level)
    )
    evidence_by_region: dict[str, dict[str, int]] = {}
    for region, severity, count in evidence_rows.all():
        if not region:
            continue
        bucket = evidence_by_region.setdefault(region, {"total": 0, "CRITICAL": 0})
        bucket["total"] += count
        if severity == SeverityLevel.CRITICAL:
            bucket["CRITICAL"] += count

    summaries: list[RegionSummary] = []

    for region, t_count, avg_conf in target_rows.all():
        ev = evidence_by_region.get(region, {})
        summaries.append(
            RegionSummary(
                region=region or "Unknown",
                target_count=t_count,
                accused_count=accused_map.get(region, 0),
                evidence_count=ev.get("total", 0),
                critical_evidence=ev.get("CRITICAL", 0),
                avg_confidence=float(avg_conf or 0),
            )
        )

    for region, a_count in accused_map.items():
        if not any(s.region == region for s in summaries):
            ev = evidence_by_region.get(region, {})
            summaries.append(
                RegionSummary(
                    region=region,
                    target_count=0,
                    accused_count=a_count,
                    evidence_count=ev.get("total", 0),
                    critical_evidence=ev.get("CRITICAL", 0),
                    avg_confidence=0.0,
                )
            )

    summaries.sort(key=lambda x: x.target_count + x.accused_count, reverse=True)
    return summaries


@router.get("/{region_name}", response_model=RegionDetail)
async def region_detail(
    region_name: str,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> RegionDetail:
    """Targets, accused, and evidence severity breakdown for one region."""
    targets_result = await session.execute(
        select(TargetAccount)
        .where(TargetAccount.inferred_region == region_name)
        .limit(50)
    )
    targets = [
        {
            "username": t.username,
            "platform": t.platform.value,
            "region_confidence": t.region_confidence,
        }
        for t in targets_result.scalars().all()
    ]
    accused_result = await session.execute(
        select(AccusedProfile).where(AccusedProfile.inferred_region == region_name).limit(50)
    )
    accused = [
        {
            "username": a.username,
            "platform": a.platform.value,
            "total_incidents": a.total_incidents,
            "max_risk_score": a.max_risk_score,
        }
        for a in accused_result.scalars().all()
    ]

    Target = aliased(TargetAccount)
    sev_rows = await session.execute(
        select(EvidenceReport.severity_level, func.count())
        .join(Target, EvidenceReport.target_id == Target.id)
        .where(Target.inferred_region == region_name)
        .group_by(EvidenceReport.severity_level)
    )
    evidence_by_severity = {s.value: c for s, c in sev_rows.all()}

    if not targets and not accused and not evidence_by_severity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data for region '{region_name}'",
        )

    return RegionDetail(
        region=region_name,
        targets=targets,
        accused=accused,
        evidence_by_severity=evidence_by_severity,
    )
