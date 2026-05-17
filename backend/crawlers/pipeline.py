"""
End-to-end crawl pipeline: fetch comments → store → classify → evidence.

Runs synchronously (usable without Redis). Called from API, CLI, or queue worker.
"""

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
    AIResult,
    CrawledComment,
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
from utils.logger import get_logger

logger = get_logger(__name__)


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
) -> dict:
    """
    Crawl one target, persist new comments, classify, create evidence when abusive.
    Returns summary dict for API responses.
    """
    result = await session.execute(select(TargetAccount).where(TargetAccount.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise ValueError(f"Target not found: {target_id}")
    if not target.is_active or not target.monitoring_enabled:
        raise ValueError(f"Target {target.username} is not active for monitoring")

    platform = target.platform
    try:
        crawler_cls = get_crawler_class(platform)
    except ValueError as exc:
        raise ValueError(
            f"Patrol not enabled for {platform.value}. "
            f"Active platforms: instagram, facebook, twitter, threads."
        ) from exc
    known_hashes = await _load_known_hashes(session, target.id)

    log = MonitoringLog(
        target_id=target.id,
        platform=platform,
        started_at=datetime.now(timezone.utc),
    )
    session.add(log)
    await session.flush()

    abusive_count = 0
    critical_count = 0
    new_count = 0

    demo_mode = False
    async with crawler_cls() as crawler:
        demo_mode = getattr(crawler, "demo_mode", False)
        crawl_result = await crawler.crawl_target_profile(
            target.username,
            max_comments=max_comments,
            known_hashes=known_hashes,
        )

        if not crawl_result.success:
            log.success = False
            log.error_message = crawl_result.error
            log.completed_at = datetime.now(timezone.utc)
            log.duration_seconds = crawl_result.duration_seconds
            await session.commit()
            return {
                "target_id": str(target_id),
                "success": False,
                "error": crawl_result.error,
                "comments_new": 0,
                "abusive_detected": 0,
            }

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
            "success": True,
            "comments_new": new_count,
            "abusive_detected": abusive_count,
            "critical_detected": critical_count,
            "duration_seconds": crawl_result.duration_seconds,
            "demo_mode": demo_mode,
        }


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
            summary = await run_crawl_for_target(session, target.id)
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
