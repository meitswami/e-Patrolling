"""Crawler control API — trigger crawls, view status and logs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.crawler import (
    CrawlResultSummary,
    CrawlTriggerResponse,
    CrawlerStatusResponse,
    MonitoringLogItem,
    PlatformPatrolInfo,
)
from auth.middleware import get_current_user
from auth.rbac import require_analyst
from configs.settings import settings
from services import system_settings as app_settings
from crawlers.pipeline import run_crawl_for_target, run_crawl_all_active
from crawlers.registry import platform_catalog, supported_platforms
from database.connection import get_session
from database.models import MonitoringLog, TargetAccount, User
from task_queue.producer import is_redis_available
from task_queue.scheduler import get_scheduler_state
from task_queue.tasks import schedule_crawl_all, schedule_crawl_target

router = APIRouter()


@router.get("/status", response_model=CrawlerStatusResponse)
async def crawler_status(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> CrawlerStatusResponse:
    """Crawler subsystem status and platform patrol catalog."""
    target_rows = await session.execute(
        select(
            TargetAccount.platform,
            func.count().label("total"),
            func.count()
            .filter(TargetAccount.monitoring_enabled.is_(True))
            .label("monitoring"),
        )
        .where(TargetAccount.is_active.is_(True))
        .group_by(TargetAccount.platform)
    )
    counts: dict[str, tuple[int, int]] = {}
    for platform, total, monitoring in target_rows.all():
        counts[platform.value] = (total or 0, monitoring or 0)

    catalog = platform_catalog()
    platforms: list[PlatformPatrolInfo] = []
    for item in catalog["active"]:
        pid = item["id"]
        total, monitoring = counts.get(pid, (0, 0))
        platforms.append(
            PlatformPatrolInfo(
                id=pid,
                label=item["label"],
                status="active",
                patrol_enabled=True,
                target_count=total,
                monitoring_count=monitoring,
            )
        )
    for item in catalog["roadmap"]:
        platforms.append(
            PlatformPatrolInfo(
                id=item["id"],
                label=item["label"],
                status="roadmap",
                patrol_enabled=False,
                target_count=0,
                monitoring_count=0,
            )
        )

    sched = get_scheduler_state()
    return CrawlerStatusResponse(
        supported_platforms=supported_platforms(),
        platforms=platforms,
        redis_enabled=is_redis_available(),
        scheduler_enabled=settings.CRAWLER_SCHEDULER_ENABLED,
        crawl_interval_seconds=settings.CRAWL_INTERVAL_SECONDS,
        demo_mode=app_settings.get_crawler_demo_mode(),
        scheduler_is_running=bool(sched.get("is_running")),
        scheduler_last_run_at=sched.get("last_run_at"),
        scheduler_last_run_status=sched.get("last_run_status"),
        scheduler_last_run_message=sched.get("last_run_message"),
        evidence_screenshot_mode=app_settings.get_evidence_screenshot_mode(),
    )


@router.post("/start/{platform}/{target_id}", response_model=CrawlTriggerResponse)
async def start_crawl_by_platform(
    platform: str,
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlTriggerResponse:
    """Alias route matching task_tracker spec (platform in path)."""
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    if target.platform.value != platform.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target platform is {target.platform.value}, not {platform}",
        )
    mode = await schedule_crawl_target(target_id, run_inline_if_no_redis=True)
    return CrawlTriggerResponse(status=mode, target_id=target_id, message=f"Crawl {mode}")


@router.post("/start/{target_id}", response_model=CrawlTriggerResponse)
async def start_crawl_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlTriggerResponse:
    """Queue or run inline crawl for one target."""
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    mode = await schedule_crawl_target(target_id, run_inline_if_no_redis=True)
    return CrawlTriggerResponse(
        status=mode,
        target_id=target_id,
        message=f"Crawl {mode} for target {target_id}",
    )


@router.post("/run/{target_id}", response_model=CrawlResultSummary)
async def run_crawl_sync(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlResultSummary:
    """Run crawl immediately and return results (blocking)."""
    try:
        summary = await run_crawl_for_target(session, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CrawlResultSummary(**summary)


@router.post("/run-all", response_model=list[CrawlResultSummary])
async def run_crawl_all_sync(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> list[CrawlResultSummary]:
    """Crawl all active targets synchronously (guarded against overlap)."""
    from task_queue.scheduler import CrawlInProgressError, crawl_all_lock

    try:
        async with crawl_all_lock():
            summaries = await run_crawl_all_active(session)
            ok = sum(1 for s in summaries if s.get("success"))
            from task_queue.scheduler import _scheduler_state

            _scheduler_state["last_run_message"] = f"Manual crawl-all: {ok}/{len(summaries)} targets"
    except CrawlInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return [CrawlResultSummary(**s) for s in summaries]


@router.post("/schedule-all", response_model=CrawlTriggerResponse)
async def schedule_all_crawls(
    _user: User = Depends(require_analyst),
) -> CrawlTriggerResponse:
    mode = await schedule_crawl_all(run_inline_if_no_redis=True)
    return CrawlTriggerResponse(status=mode, message=f"Crawl-all {mode}")


@router.get("/logs", response_model=list[MonitoringLogItem])
async def list_crawl_logs(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[MonitoringLogItem]:
    result = await session.execute(
        select(MonitoringLog).order_by(MonitoringLog.started_at.desc()).limit(limit)
    )
    return [MonitoringLogItem.model_validate(row) for row in result.scalars().all()]
