"""Crawler control API — trigger crawls, view status and logs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.crawler import (
    CrawlLogEvidenceItem,
    CrawlLogResultsResponse,
    CrawlResultSummary,
    CrawlTriggerResponse,
    CrawlerStatusResponse,
    MonitoringLogItem,
    PlatformPatrolInfo,
    RunningCrawlInfo,
)
from auth.middleware import get_current_user
from auth.rbac import require_admin, require_analyst
from configs.settings import settings
from services import system_settings as app_settings
from crawlers.pipeline import reclassify_log_comments, run_crawl_for_target, run_crawl_all_active
from crawlers.registry import platform_catalog, supported_platforms
from database.connection import get_session
from api.helpers.evidence_abuse import apply_evidence_abuse_fields
from database.models import AIResult, AccusedProfile, EvidenceReport, MonitoringLog, TargetAccount, User
from crawlers.crawl_state import list_running
from task_queue.producer import is_redis_available
from task_queue.scheduler import get_scheduler_state, request_crawl_stop
from task_queue.tasks import schedule_crawl_all, schedule_crawl_target, schedule_view_crawl_target

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
    err_result = await session.execute(
        select(MonitoringLog)
        .where(MonitoringLog.success.is_(False))
        .order_by(MonitoringLog.started_at.desc())
        .limit(5)
    )
    recent_errors = [
        {
            "platform": log.platform.value,
            "target_id": str(log.target_id) if log.target_id else None,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
        }
        for log in err_result.scalars().all()
    ]
    return CrawlerStatusResponse(
        supported_platforms=supported_platforms(),
        platforms=platforms,
        redis_enabled=is_redis_available(),
        scheduler_enabled=settings.CRAWLER_SCHEDULER_ENABLED,
        crawl_interval_seconds=settings.CRAWL_INTERVAL_SECONDS,
        mode="live",
        instagram_credentials_configured=app_settings.instagram_auth_configured(),
        running_targets=[RunningCrawlInfo(**r) for r in list_running()],
        scheduler_is_running=bool(sched.get("is_running")),
        scheduler_last_run_at=sched.get("last_run_at"),
        scheduler_last_run_status=sched.get("last_run_status"),
        scheduler_last_run_message=sched.get("last_run_message"),
        evidence_screenshot_mode=app_settings.get_evidence_screenshot_mode(),
        crawl_stop_requested=bool(sched.get("stop_requested")),
        recent_errors=recent_errors,
        last_export_at=sched.get("last_export_at"),
        last_export_path=sched.get("last_export_path"),
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
        msg = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "already running" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg) from exc
    return CrawlResultSummary(**summary)


@router.post("/start/{target_id}/view", response_model=CrawlTriggerResponse)
async def start_view_crawl_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlTriggerResponse:
    """Queue view crawl — opens visible browser; monitor via live feed."""
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    from crawlers.crawl_state import is_target_running

    if is_target_running(target_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Crawl already running for this target",
        )
    mode = await schedule_view_crawl_target(target_id)
    return CrawlTriggerResponse(
        status=mode,
        target_id=target_id,
        message=f"View crawl {mode} — visible browser will open on this PC",
    )


@router.post("/start/{target_id}/view/historical", response_model=CrawlTriggerResponse)
async def start_view_historical_crawl_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlTriggerResponse:
    """Queue historical view crawl with visible browser."""
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    from crawlers.crawl_state import is_target_running

    if is_target_running(target_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Crawl already running for this target",
        )
    mode = await schedule_view_crawl_target(target_id, historical=True)
    return CrawlTriggerResponse(
        status=mode,
        target_id=target_id,
        message=f"Historical view crawl {mode}",
    )


@router.post("/run/{target_id}/view", response_model=CrawlResultSummary)
async def run_view_crawl_sync(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlResultSummary:
    """Run crawl with visible browser + live feed (View Crawling mode)."""
    try:
        summary = await run_crawl_for_target(session, target_id, view_mode=True)
    except ValueError as exc:
        msg = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "already running" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg) from exc
    return CrawlResultSummary(**summary)


@router.post("/run/{target_id}/view/historical", response_model=CrawlResultSummary)
async def run_view_historical_crawl_sync(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlResultSummary:
    """Historical crawl with visible browser (View Crawling mode)."""
    try:
        summary = await run_crawl_for_target(
            session, target_id, historical=True, view_mode=True
        )
    except ValueError as exc:
        msg = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "already running" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg) from exc
    return CrawlResultSummary(**summary)


@router.post("/{target_id}/pause")
async def pause_target_crawl(
    target_id: UUID,
    _user: User = Depends(require_analyst),
) -> dict:
    """Pause an in-flight view crawl for this target."""
    from services.crawl_view_state import crawl_view_state

    if not crawl_view_state.pause(str(target_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No running view crawl to pause for this target",
        )
    return {"status": "paused", "target_id": str(target_id)}


@router.post("/{target_id}/resume")
async def resume_target_crawl(
    target_id: UUID,
    _user: User = Depends(require_analyst),
) -> dict:
    """Resume a paused view crawl for this target."""
    from services.crawl_view_state import crawl_view_state

    if not crawl_view_state.resume(str(target_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No paused view crawl to resume for this target",
        )
    return {"status": "resumed", "target_id": str(target_id)}


@router.post("/{target_id}/stop")
async def stop_target_crawl(
    target_id: UUID,
    _user: User = Depends(require_analyst),
) -> dict:
    """Stop an in-flight view crawl for this target."""
    from services.crawl_view_state import crawl_view_state

    if not crawl_view_state.stop(str(target_id)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active view crawl to stop for this target",
        )
    return {"status": "stopped", "target_id": str(target_id)}


@router.get("/{target_id}/view-status")
async def target_crawl_view_status(
    target_id: UUID,
    _user: User = Depends(get_current_user),
) -> dict:
    """View crawl pause/resume state for a target."""
    from services.crawl_view_state import crawl_view_state

    return crawl_view_state.get_status(str(target_id))


@router.post("/run/{target_id}/historical", response_model=CrawlResultSummary)
async def run_historical_crawl_sync(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> CrawlResultSummary:
    """
    Deep crawl: scroll older posts on the profile and collect comments on each post.
    Instagram only (other platforms fall back to a regular crawl).
    """
    try:
        summary = await run_crawl_for_target(session, target_id, historical=True)
    except ValueError as exc:
        msg = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if "already running" in msg.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=msg) from exc
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


@router.post("/stop")
async def stop_crawl_all(
    _user: User = Depends(require_analyst),
) -> dict:
    """Request graceful stop of an in-progress crawl-all after the current target."""
    request_crawl_stop()
    return {"status": "stop_requested", "message": "Crawl-all will stop after the current target"}


@router.get("/job")
async def crawl_job_status(
    _user: User = Depends(get_current_user),
) -> dict:
    """Current crawl job / scheduler snapshot."""
    return get_scheduler_state()


@router.post("/logs/clear-errors")
async def clear_crawl_error_logs(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
    all_failed: bool = Query(
        False,
        description="If true, remove every failed log. Default: only legacy login-timeout errors.",
    ),
) -> dict:
    """
    Remove stale failed crawl logs from the UI (does not stop running crawlers).
    """
    from sqlalchemy import delete

    q = delete(MonitoringLog).where(MonitoringLog.success.is_(False))
    if not all_failed:
        q = q.where(
            MonitoringLog.error_message.isnot(None),
            MonitoringLog.error_message.contains("Page.fill"),
        )
    result = await session.execute(q)
    await session.commit()
    removed = result.rowcount or 0
    return {"removed": removed, "message": f"Cleared {removed} failed log(s)."}

@router.get("/logs", response_model=list[MonitoringLogItem])
async def list_crawl_logs(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[MonitoringLogItem]:
    result = await session.execute(
        select(MonitoringLog, TargetAccount.username)
        .outerjoin(TargetAccount, MonitoringLog.target_id == TargetAccount.id)
        .order_by(MonitoringLog.started_at.desc())
        .limit(limit)
    )
    items: list[MonitoringLogItem] = []
    for log, target_username in result.all():
        item = MonitoringLogItem.model_validate(log)
        item.target_username = target_username
        items.append(item)
    return items


@router.get("/logs/{log_id}/results", response_model=CrawlLogResultsResponse)
async def crawl_log_results(
    log_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> CrawlLogResultsResponse:
    """Evidence and offenders captured during a specific crawl run."""
    log_row = await session.execute(
        select(MonitoringLog, TargetAccount.username)
        .outerjoin(TargetAccount, MonitoringLog.target_id == TargetAccount.id)
        .where(MonitoringLog.id == log_id)
    )
    row = log_row.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl log not found")
    log, target_username = row

    evidence_q = (
        select(EvidenceReport, AccusedProfile.username, AIResult)
        .outerjoin(AccusedProfile, EvidenceReport.accused_id == AccusedProfile.id)
        .outerjoin(AIResult, EvidenceReport.ai_result_id == AIResult.id)
    )
    if log.target_id and log.started_at:
        evidence_q = evidence_q.where(EvidenceReport.target_id == log.target_id)
        # Add a small buffer (5 seconds) to account for clock differences between
        # Python-set started_at/completed_at and DB server_default capture_timestamp
        from datetime import timedelta
        buffer = timedelta(seconds=5)
        start_bound = log.started_at - buffer
        if log.completed_at:
            end_bound = log.completed_at + buffer
            evidence_q = evidence_q.where(
                EvidenceReport.capture_timestamp >= start_bound,
                EvidenceReport.capture_timestamp <= end_bound,
            )
        else:
            evidence_q = evidence_q.where(EvidenceReport.capture_timestamp >= start_bound)
    elif log.target_id:
        evidence_q = evidence_q.where(EvidenceReport.target_id == log.target_id)

    evidence_q = evidence_q.order_by(EvidenceReport.capture_timestamp.desc())
    ev_result = await session.execute(evidence_q)
    evidence_items: list[CrawlLogEvidenceItem] = []
    for ev, accused_username, ai_row in ev_result.all():
        item = CrawlLogEvidenceItem(
            evidence_id=ev.evidence_id,
            uuid=ev.id,
            accused_username=accused_username,
            severity=ev.severity_level.value,
            risk_score=ev.risk_score,
            comment_preview=(ev.comment_text or "")[:200],
            screenshot_path=ev.screenshot_path,
        )
        apply_evidence_abuse_fields(item, ev, ai_row)
        evidence_items.append(item)

    return CrawlLogResultsResponse(
        log_id=log.id,
        target_id=log.target_id,
        target_username=target_username,
        platform=log.platform.value,
        success=log.success,
        comments_new=log.comments_new,
        abusive_detected=log.abusive_detected,
        started_at=log.started_at,
        completed_at=log.completed_at,
        evidence=evidence_items,
    )


@router.post("/logs/{log_id}/reclassify")
async def reclassify_crawl_log(
    log_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> dict:
    """Re-run abuse detection on comments from this crawl (e.g. after lexicon update)."""
    try:
        return await reclassify_log_comments(session, log_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
