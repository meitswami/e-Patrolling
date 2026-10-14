"""
End-to-end crawl pipeline: fetch comments → store → classify → evidence.

Runs synchronously (usable without Redis). Called from API, CLI, or queue worker.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.classifier import classify_comment
from ai.language_detector import detect_language
from configs.settings import settings
from crawlers.registry import get_crawler_class
from database.models import (
    AccusedProfile,
    AIResult,
    CrawledComment,
    EvidenceReport,
    LanguageType,
    MonitoringLog,
    PlatformType,
    TargetAccount,
)
from evidence.collector import (
    create_evidence_from_classification,
    generate_evidence_id,
    get_or_create_accused,
)
from crawlers.crawl_state import (
    is_target_running,
    register_running,
    unregister_running,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# Global semaphore enforcing MAX_CONCURRENT_BROWSERS. Prevents memory exhaustion
# from too many Chromium instances running simultaneously.
_browser_semaphore: Optional[asyncio.Semaphore] = None


def _get_browser_semaphore() -> asyncio.Semaphore:
    """Lazy-init semaphore (must be created inside a running event loop)."""
    global _browser_semaphore
    if _browser_semaphore is None:
        _browser_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_BROWSERS)
    return _browser_semaphore


# Per-target crawl timeout: regular=5min, historical=15min
_CRAWL_TIMEOUT_REGULAR = 300
_CRAWL_TIMEOUT_HISTORICAL = 900


def _mark_log_completed(log: MonitoringLog) -> None:
    log.completed_at = datetime.now(timezone.utc)
    if log.started_at:
        log.duration_seconds = (log.completed_at - log.started_at).total_seconds()


async def _load_known_hashes(session: AsyncSession, target_id: UUID) -> set[str]:
    result = await session.execute(
        select(CrawledComment.content_hash).where(CrawledComment.target_id == target_id)
    )
    return {row[0] for row in result.all()}


async def run_crawl_for_target(
    session: AsyncSession,
    target_id: UUID,
    *,
    max_comments: int = 50,
    crawl_mode: str = "single",
    historical: bool = False,
    view_mode: bool = False,
) -> dict:
    """
    Crawl one target, persist new comments, classify, create evidence when abusive.

    Regular crawl: profile page snapshot (good for new activity since last run).
    Historical crawl: scroll older posts and collect comments on each post.
    Returns summary dict for API responses.
    """
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise ValueError(f"Target not found: {target_id}")
    if not target.is_active or not target.monitoring_enabled:
        raise ValueError(f"Target {target.username} is not active for monitoring")
    if is_target_running(target_id):
        raise ValueError(f"Crawl already running for @{target.username}")

    platform = target.platform
    run_mode = "view_historical" if (view_mode and historical) else (
        "view" if view_mode else ("historical" if historical else crawl_mode)
    )

    from services import system_settings as app_settings

    if platform == PlatformType.INSTAGRAM and not app_settings.instagram_auth_configured():
        raise ValueError(
            "Instagram not connected. Open Settings → Connect Instagram, log in in the "
            "browser window, then crawl again."
        )

    register_running(
        target.id,
        target.username,
        platform.value,
        mode=run_mode,
    )
    try:
        crawler_cls = get_crawler_class(platform)
    except ValueError as exc:
        raise ValueError(
            f"Patrol not enabled for {platform.value}. "
            f"Active platforms: instagram, facebook, twitter, threads."
        ) from exc
    known_hashes = await _load_known_hashes(session, target.id)

    from services.crawl_checkpoint import load_target_checkpoint, save_target_checkpoint

    checkpoint = await load_target_checkpoint(session, target)

    async def _persist_checkpoint() -> None:
        await save_target_checkpoint(session, checkpoint, flush_only=True)

    log = MonitoringLog(
        target_id=target.id,
        platform=platform,
        started_at=datetime.now(timezone.utc),
        crawl_mode=run_mode,
    )
    session.add(log)
    await session.flush()

    from crawlers.crawl_context import reset_crawl_log_id, set_crawl_log_id
    from services.crawl_session_tracker import start_tracking, stop_tracking

    set_crawl_log_id(log.id)
    await start_tracking(log.id)

    abusive_count = 0
    critical_count = 0
    new_count = 0
    evidence_ids_created: list[str] = []

    run_historical = historical and platform == PlatformType.INSTAGRAM

    try:
        sem = _get_browser_semaphore()
        crawl_timeout = _CRAWL_TIMEOUT_HISTORICAL if run_historical else _CRAWL_TIMEOUT_REGULAR

        from websocket.events import broadcast_crawl_activity

        await broadcast_crawl_activity(
            target_username=target.username,
            activity_type="crawl_started",
            message=f"Starting {'historical' if run_historical else 'regular'} crawl for @{target.username}",
            platform=platform.value,
        )

        crawler_ctor_kwargs: dict = {}
        if view_mode:
            from services.crawl_view_state import crawl_view_state

            crawl_view_state.start(str(target_id), view_mode=True)
            # Headed browser only when explicitly configured (local dev). VPS has no display —
            # live feed still streams all crawl steps over WebSocket in headless mode.
            if not settings.CRAWLER_HEADLESS:
                crawler_ctor_kwargs["headless"] = False

        async with sem:
            async with crawler_cls(**crawler_ctor_kwargs) as crawler:
                crawl_kwargs: dict = {
                    "max_comments": max_comments,
                    "known_hashes": known_hashes,
                    "crawl_target_id": str(target_id) if view_mode else None,
                }
                if run_historical:
                    crawl_kwargs["historical"] = True
                    crawl_kwargs["max_posts"] = settings.HISTORICAL_CRAWL_MAX_POSTS
                    crawl_kwargs["max_comments_per_post"] = settings.HISTORICAL_CRAWL_MAX_COMMENTS_PER_POST
                    crawl_kwargs["checkpoint"] = checkpoint
                    crawl_kwargs["on_post_saved"] = _persist_checkpoint
                elif historical:
                    logger.warning(
                        "Historical crawl not supported for %s — using regular crawl",
                        platform.value,
                    )

                try:
                    crawl_result = await asyncio.wait_for(
                        crawler.crawl_target_profile(
                            target.username,
                            **crawl_kwargs,
                        ),
                        timeout=crawl_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "Crawl timed out for @%s after %ds",
                        target.username,
                        crawl_timeout,
                    )
                    log.success = False
                    log.error_message = f"Crawl timed out after {crawl_timeout}s"
                    _mark_log_completed(log)
                    await session.commit()
                    return {
                        "target_id": str(target_id),
                        "target_username": target.username,
                        "platform": platform.value,
                        "log_id": str(log.id),
                        "historical": run_historical,
                        "posts_crawled": 0,
                        "success": False,
                        "error": f"Crawl timed out after {crawl_timeout}s",
                        "comments_new": 0,
                        "abusive_detected": 0,
                        "evidence_ids": [],
                    }

                if not crawl_result.success:
                    log.success = False
                    err = crawl_result.error or "Crawl failed"
                    if "Browser session" in err or "not initialized" in err:
                        err = (
                            f"{err}. Restart the API without --reload, run "
                            "`python -m playwright install chromium` in backend/.venv, "
                            "and connect Instagram in Settings (session cookies)."
                        )
                    log.error_message = err
                    _mark_log_completed(log)
                    log.duration_seconds = crawl_result.duration_seconds
                    await session.commit()
                    return {
                        "target_id": str(target_id),
                        "target_username": target.username,
                        "platform": platform.value,
                        "log_id": str(log.id),
                        "historical": run_historical,
                        "posts_crawled": crawl_result.pages_crawled or 0,
                        "success": False,
                        "error": crawl_result.error,
                        "comments_new": 0,
                        "abusive_detected": 0,
                        "evidence_ids": [],
                    }

                demo_mode = getattr(crawler, "demo_mode", False)

                for raw in crawl_result.comments:
                    content_hash = raw.content_hash()
                    if content_hash in known_hashes:
                        continue
                    known_hashes.add(content_hash)

                    from osint.avatar_hash import compute_avatar_hash

                    accused_bio = raw.raw_data.get("accused_bio") or raw.raw_data.get("bio")
                    avatar_url = raw.accused_avatar_url or raw.raw_data.get("accused_avatar_url")
                    avatar_hash = await compute_avatar_hash(avatar_url) if avatar_url else None

                    accused = await get_or_create_accused(
                        session,
                        platform=platform,
                        username=raw.accused_username or "unknown",
                        profile_url=raw.accused_profile_url or f"https://instagram.com/{raw.accused_username}",
                        display_name=raw.accused_display_name,
                        avatar_url=avatar_url or None,
                        bio=accused_bio,
                        avatar_hash=avatar_hash,
                    )

                    detected = detect_language(raw.text)
                    lang = detected.language
                    if raw.language_hint:
                        try:
                            lang = LanguageType(raw.language_hint.lower())
                        except ValueError:
                            pass

                    db_comment = CrawledComment(
                        content_hash=content_hash,
                        platform=platform,
                        post_url=raw.post_url,
                        post_id=raw.post_id or None,
                        comment_id=raw.comment_id or None,
                        comment_url=raw.comment_url,
                        text=raw.text,
                        language=lang,
                        target_id=target.id,
                        accused_id=accused.id,
                        platform_timestamp=raw.timestamp,
                        raw_data=raw.raw_data,
                        is_processed=True,
                        processed_at=datetime.now(timezone.utc),
                    )
                    session.add(db_comment)
                    await session.flush()
                    new_count += 1

                    classification = classify_comment(raw.text, lang.value)
                    if not classification.is_abusive:
                        continue

                    abusive_count += 1
                    if classification.severity_level.value == "CRITICAL":
                        critical_count += 1

                    await broadcast_crawl_activity(
                        target_username=target.username,
                        activity_type="comment_abusive",
                        message=f"Abusive [{classification.severity_level.value}]: {raw.text[:80]}",
                        detail=f"by @{raw.accused_username} — score {classification.risk_score}",
                        platform=platform.value,
                    )

                    ai_row = AIResult(
                        comment_id=db_comment.id,
                        is_abusive=True,
                        is_sexual_harassment=classification.is_sexual_harassment,
                        is_rape_threat=classification.is_rape_threat,
                        is_stalking=classification.is_stalking,
                        is_threat=classification.is_threat,
                        is_bullying=classification.is_bullying,
                        confidence_score=classification.confidence_score,
                        toxicity_score=classification.toxicity_score,
                        severity_score=classification.severity_score,
                        risk_score=classification.risk_score,
                        severity_level=classification.severity_level,
                        detected_language=classification.detected_language,
                        matched_keywords=classification.matched_keywords,
                        model_used=classification.model_used,
                    )
                    session.add(ai_row)
                    await session.flush()

                    from osint.permaliinks import build_comment_permalink, build_permalink_snapshot

                    comment_url = raw.comment_url or build_comment_permalink(
                        platform.value,
                        username=raw.accused_username or accused.username,
                        post_id=raw.post_id or "",
                        comment_id=raw.comment_id or "",
                        post_url=raw.post_url,
                    )
                    if comment_url and not db_comment.comment_url:
                        db_comment.comment_url = comment_url

                    eid = generate_evidence_id()
                    from evidence.screenshot_engine import capture_evidence_artifacts

                    screenshot_path = await capture_evidence_artifacts(
                        crawler,
                        evidence_id=eid,
                        platform=platform.value,
                        comment_text=raw.text,
                        accused_username=raw.accused_username or accused.username,
                        target_username=target.username,
                        severity=classification.severity_level.value,
                        post_url=raw.post_url,
                        page_url=comment_url or raw.post_url,
                        comment_url=comment_url,
                        comment_posted_at=raw.timestamp.isoformat() if raw.timestamp else None,
                        demo_mode=demo_mode,
                    )

                    screenshot_hash = None
                    if screenshot_path:
                        from evidence.metadata import resolve_screenshot_path, sha256_file

                        abs_path = resolve_screenshot_path(
                            screenshot_path, settings.EVIDENCE_STORAGE_PATH
                        )
                        screenshot_hash = sha256_file(abs_path)

                    permalink_snapshot = build_permalink_snapshot(
                        platform=platform.value,
                        username=raw.accused_username or accused.username,
                        post_url=raw.post_url,
                        comment_url=comment_url,
                        post_id=raw.post_id,
                        comment_id=raw.comment_id,
                        comment_posted_at=raw.timestamp.isoformat() if raw.timestamp else None,
                        captured_at=datetime.now(timezone.utc).isoformat(),
                        raw_data=raw.raw_data,
                    )
                    if classification.abuse_categories:
                        permalink_snapshot["abuse_categories"] = classification.abuse_categories
                    from ai.abuse_explanations import build_abuse_explanations

                    permalink_snapshot["abuse_explanations"] = build_abuse_explanations(
                        raw.text,
                        classification.abuse_categories,
                    )

                    evidence = await create_evidence_from_classification(
                        session,
                        comment_id=db_comment.id,
                        ai_result_id=ai_row.id,
                        target_id=target.id,
                        accused_id=accused.id,
                        platform=platform,
                        post_url=raw.post_url,
                        comment_text=raw.text,
                        comment_timestamp=raw.timestamp,
                        classification=classification,
                        screenshot_path=screenshot_path,
                        screenshot_hash=screenshot_hash,
                        evidence_id=eid,
                        comment_url=comment_url,
                        platform_comment_id=raw.comment_id or None,
                        post_id=raw.post_id or None,
                        permalink_snapshot=permalink_snapshot,
                    )

                    from websocket.events import broadcast_evidence_created

                    await broadcast_evidence_created(
                        evidence_id=evidence.evidence_id,
                        severity=classification.severity_level.value,
                        platform=platform.value,
                        target_username=target.username,
                        comment_preview=raw.text,
                        risk_score=classification.risk_score,
                    )
                    evidence_ids_created.append(evidence.evidence_id)

                    accused.total_incidents += 1
                    if classification.severity_level.value == "CRITICAL":
                        accused.critical_count += 1
                    elif classification.severity_level.value == "HIGH":
                        accused.high_count += 1
                    accused.max_risk_score = max(accused.max_risk_score, classification.risk_score)
                    accused.last_seen_at = datetime.now(timezone.utc)

                target.last_crawled_at = datetime.now(timezone.utc)
                log.comments_found = len(crawl_result.comments)
                log.comments_new = new_count
                log.abusive_detected = abusive_count
                log.critical_detected = critical_count
                log.duration_seconds = crawl_result.duration_seconds
                log.pages_crawled = crawl_result.pages_crawled
                log.success = True
                log.completed_at = datetime.now(timezone.utc)
                if run_historical and crawl_result.crawl_progress:
                    log.crawl_progress = crawl_result.crawl_progress
                    await save_target_checkpoint(session, checkpoint)

                # Profile intelligence: observe the subject's OWN public profile
                # and record identity changes (name/bio/verification) over time.
                # Best effort — never fail a crawl because this couldn't run.
                if settings.PROFILE_INTELLIGENCE_ENABLED:
                    try:
                        from services.profile_intelligence import record_profile_observation
                        from services.profile_lookup import lookup_profile

                        info = await lookup_profile(platform.value, target.username)
                        if info and getattr(info, "found", False):
                            observed = {
                                "display_name": info.full_name,
                                "bio": info.bio,
                                "follower_count": info.followers,
                                "following_count": info.following,
                                "posts_count": info.posts_count,
                                "is_verified": info.is_verified,
                                "is_private": info.is_private,
                            }
                            tracked = await record_profile_observation(
                                session, target.id, observed
                            )
                            if tracked:
                                logger.info(
                                    "Profile change(s) on @%s: %s",
                                    target.username,
                                    ", ".join(c["field"] for c in tracked),
                                )
                    except Exception as exc:
                        logger.debug(
                            "Profile observation skipped for @%s: %s",
                            target.username,
                            exc,
                        )

                await session.commit()

                from websocket.events import broadcast_crawl_completed

                await broadcast_crawl_completed(
                    target_username=target.username,
                    comments_new=new_count,
                    abusive_detected=abusive_count,
                    success=True,
                )

                logger.info(
                    "Crawl complete @%s: %d new, %d abusive",
                    target.username,
                    new_count,
                    abusive_count,
                )

                return {
                    "target_id": str(target_id),
                    "target_username": target.username,
                    "platform": platform.value,
                    "log_id": str(log.id),
                    "historical": run_historical,
                    "posts_crawled": crawl_result.pages_crawled or 0,
                    "success": True,
                    "comments_new": new_count,
                    "abusive_detected": abusive_count,
                    "critical_detected": critical_count,
                    "duration_seconds": crawl_result.duration_seconds,
                    "evidence_ids": evidence_ids_created,
                }
    except Exception as exc:
        from services.crawl_pause import CrawlPausedStop

        if isinstance(exc, CrawlPausedStop):
            log.success = False
            log.error_message = "Crawl stopped by operator"
            _mark_log_completed(log)
            await session.commit()
            return {
                "target_id": str(target_id),
                "target_username": target.username,
                "platform": platform.value,
                "log_id": str(log.id),
                "historical": run_historical,
                "success": False,
                "error": "Crawl stopped by operator",
                "comments_new": new_count,
                "abusive_detected": abusive_count,
                "evidence_ids": evidence_ids_created,
            }
        try:
            from websocket.events import broadcast_crawl_activity

            await broadcast_crawl_activity(
                target_username=target.username,
                activity_type="crawl_error",
                message=str(exc)[:500],
                platform=platform.value,
            )
        except Exception:
            pass
        if log.id:
            log.success = False
            log.error_message = str(exc)[:2000]
            _mark_log_completed(log)
            await session.commit()
        raise
    finally:
        try:
            session_data = await stop_tracking(log.id)
            if session_data:
                log.session_data = session_data
                log.crawl_mode = run_mode
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist crawl session data for log %s: %s", log.id, exc)
        reset_crawl_log_id()
        unregister_running(target_id)
        if view_mode:
            from services.crawl_view_state import crawl_view_state

            crawl_view_state.reset(str(target_id))


async def run_crawl_all_active(session: AsyncSession) -> list[dict]:
    """Crawl every active, monitoring-enabled target on patrol-enabled platforms."""
    from crawlers.registry import is_patrol_platform

    result = await session.execute(
        select(TargetAccount).where(
            TargetAccount.is_active.is_(True),
            TargetAccount.monitoring_enabled.is_(True),
        )
    )
    targets = result.scalars().all()
    summaries = []
    from task_queue.scheduler import clear_crawl_stop, is_crawl_stop_requested

    for target in targets:
        if is_crawl_stop_requested():
            logger.warning("Crawl-all stopped by operator request")
            clear_crawl_stop()
            break
        if not is_patrol_platform(target.platform):
            logger.info(
                "Skipping @%s (%s) — patrol not enabled for this platform yet",
                target.username,
                target.platform.value,
            )
            continue
        try:
            summary = await run_crawl_for_target(session, target.id, crawl_mode="crawl_all")
            summaries.append(summary)
        except Exception as exc:
            logger.error("Crawl failed for %s: %s", target.username, exc)
            summaries.append(
                {
                    "target_id": str(target.id),
                    "target_username": target.username,
                    "success": False,
                    "error": str(exc),
                }
            )
    return summaries


async def reclassify_log_comments(session: AsyncSession, log_id: UUID) -> dict:
    """Re-run abuse classifier on comments from a crawl window (after lexicon/ML fixes)."""
    log = await session.get(MonitoringLog, log_id)
    if not log or not log.target_id:
        raise ValueError("Crawl log not found")

    target = await session.get(TargetAccount, log.target_id)
    if not target:
        raise ValueError("Target not found")

    window_end = log.completed_at or datetime.now(timezone.utc)
    result = await session.execute(
        select(CrawledComment)
        .where(
            CrawledComment.target_id == log.target_id,
            CrawledComment.crawled_at >= log.started_at,
            CrawledComment.crawled_at <= window_end,
        )
        .order_by(CrawledComment.crawled_at.desc())
    )
    comments = result.scalars().all()

    newly_abusive = 0
    evidence_ids: list[str] = []
    platform = target.platform

    for db_comment in comments:
        existing_ev = await session.execute(
            select(EvidenceReport.id).where(EvidenceReport.comment_id == db_comment.id).limit(1)
        )
        if existing_ev.first():
            continue

        classification = classify_comment(db_comment.text, db_comment.language.value)
        if not classification.is_abusive:
            continue

        accused = await session.get(AccusedProfile, db_comment.accused_id) if db_comment.accused_id else None
        if not accused:
            continue

        ai_row = (
            await session.execute(
                select(AIResult).where(AIResult.comment_id == db_comment.id).limit(1)
            )
        ).scalar_one_or_none()
        if not ai_row:
            ai_row = AIResult(
                comment_id=db_comment.id,
                is_abusive=True,
                is_sexual_harassment=classification.is_sexual_harassment,
                is_rape_threat=classification.is_rape_threat,
                is_stalking=classification.is_stalking,
                is_threat=classification.is_threat,
                is_bullying=classification.is_bullying,
                confidence_score=classification.confidence_score,
                toxicity_score=classification.toxicity_score,
                severity_score=classification.severity_score,
                risk_score=classification.risk_score,
                severity_level=classification.severity_level,
                detected_language=classification.detected_language,
                matched_keywords=classification.matched_keywords,
                model_used=classification.model_used,
            )
            session.add(ai_row)
            await session.flush()

        from osint.permaliinks import build_comment_permalink, build_permalink_snapshot

        comment_url = db_comment.comment_url or build_comment_permalink(
            platform.value,
            username=accused.username,
            post_id=db_comment.post_id or "",
            comment_id=db_comment.comment_id or "",
            post_url=db_comment.post_url,
        )
        eid = generate_evidence_id()
        reclassify_snapshot = build_permalink_snapshot(
            platform=platform.value,
            username=accused.username,
            post_url=db_comment.post_url,
            comment_url=comment_url,
            post_id=db_comment.post_id,
            comment_id=db_comment.comment_id,
            comment_posted_at=(
                db_comment.platform_timestamp.isoformat()
                if db_comment.platform_timestamp
                else None
            ),
            captured_at=datetime.now(timezone.utc).isoformat(),
            raw_data=db_comment.raw_data,
        )
        if classification.abuse_categories:
            reclassify_snapshot["abuse_categories"] = classification.abuse_categories
        from ai.abuse_explanations import build_abuse_explanations

        reclassify_snapshot["abuse_explanations"] = build_abuse_explanations(
            db_comment.text or "",
            classification.abuse_categories,
        )

        evidence = await create_evidence_from_classification(
            session,
            comment_id=db_comment.id,
            ai_result_id=ai_row.id,
            target_id=target.id,
            accused_id=accused.id,
            platform=platform,
            post_url=db_comment.post_url,
            comment_text=db_comment.text,
            comment_timestamp=db_comment.platform_timestamp,
            classification=classification,
            screenshot_path=None,
            evidence_id=eid,
            comment_url=comment_url,
            platform_comment_id=db_comment.comment_id,
            post_id=db_comment.post_id,
            permalink_snapshot=reclassify_snapshot,
        )
        newly_abusive += 1
        evidence_ids.append(evidence.evidence_id)

    log.abusive_detected = (log.abusive_detected or 0) + newly_abusive
    await session.commit()
    return {
        "log_id": str(log_id),
        "comments_checked": len(comments),
        "newly_flagged_abusive": newly_abusive,
        "evidence_ids": evidence_ids,
    }
