"""Dashboard analytics endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.analytics import (
    AnalyticsOverview,
    DashboardStatsResponse,
    PlatformBreakdown,
    SeverityBreakdown,
)
from auth.middleware import get_current_user
from database.connection import get_session
from database.models import (
    EvidenceReport,
    RepeatOffender,
    SeverityLevel,
    TargetAccount,
    User,
)
from database.models import OffenderStatus

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> DashboardStatsResponse:
    """Aggregate stats for the command center dashboard."""
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    active_targets = await session.scalar(
        select(func.count()).select_from(TargetAccount).where(TargetAccount.is_active.is_(True))
    )
    evidence_24h = await session.scalar(
        select(func.count())
        .select_from(EvidenceReport)
        .where(EvidenceReport.created_at >= since_24h)
    )
    critical_total = await session.scalar(
        select(func.count())
        .select_from(EvidenceReport)
        .where(EvidenceReport.severity_level == SeverityLevel.CRITICAL)
    )
    repeat_offenders = await session.scalar(
        select(func.count())
        .select_from(RepeatOffender)
        .where(RepeatOffender.status == OffenderStatus.CONFIRMED)
    )
    total_evidence = await session.scalar(select(func.count()).select_from(EvidenceReport))

    monitoring_count = await session.scalar(
        select(func.count())
        .select_from(TargetAccount)
        .where(TargetAccount.is_active.is_(True), TargetAccount.monitoring_enabled.is_(True))
    )

    return DashboardStatsResponse(
        active_targets=active_targets or 0,
        evidence_24h=evidence_24h or 0,
        critical_total=critical_total or 0,
        repeat_offenders=repeat_offenders or 0,
        total_evidence=total_evidence or 0,
        live_monitoring=(monitoring_count or 0) > 0,
    )


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> AnalyticsOverview:
    """Dashboard stats plus severity and platform breakdowns."""
    dashboard = await get_dashboard_stats(session=session, _user=_user)

    severity_rows = await session.execute(
        select(EvidenceReport.severity_level, func.count())
        .group_by(EvidenceReport.severity_level)
    )
    sev = SeverityBreakdown()
    for level, count in severity_rows.all():
        setattr(sev, level.value, count)

    platform_rows = await session.execute(
        select(EvidenceReport.platform, func.count())
        .group_by(EvidenceReport.platform)
        .order_by(func.count().desc())
    )
    platforms = [
        PlatformBreakdown(platform=row[0].value, count=row[1]) for row in platform_rows.all()
    ]

    return AnalyticsOverview(dashboard=dashboard, by_severity=sev, by_platform=platforms)
