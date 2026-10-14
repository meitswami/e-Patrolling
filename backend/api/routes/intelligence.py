"""Profile Intelligence API.

Per-target endpoints for the monitored subject:
  - profile knowledge + change history ("was X, now Y")
  - repeat-offender ranking and coordinated pile-on detection (handle-level)
  - severity-weighted risk score
  - evidence export (JSON/CSV) for a platform report or police complaint
  - reclassify all stored comments after an Abuse Dictionary update

Everything here is grounded in data already collected on the target's own
posts. Nothing de-anonymizes the people who comment.
"""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.rbac import require_analyst
from database.connection import get_session
from database.models import AccusedProfile, EvidenceReport, MonitoringLog, TargetAccount, User
from services import profile_intelligence as pi

router = APIRouter()


async def _require_target(session: AsyncSession, target_id: UUID) -> TargetAccount:
    target = await session.get(TargetAccount, target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return target


@router.get("/{target_id}/profile")
async def target_profile_knowledge(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Current known public profile of the monitored account + change history."""
    await _require_target(session, target_id)
    return await pi.get_profile_knowledge(session, target_id)


@router.get("/{target_id}/offenders")
async def target_offenders(
    target_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    days: int = Query(365, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Handles that abuse this target most (repeat-offender ranking)."""
    await _require_target(session, target_id)
    return {"offenders": await pi.top_offenders(session, target_id, limit=limit, days=days)}


@router.get("/{target_id}/pile-on")
async def target_pile_on(
    target_id: UUID,
    window_hours: int = Query(6, ge=1, le=72),
    min_distinct_accounts: int = Query(5, ge=2, le=100),
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Time windows where many distinct accounts piled on this target at once."""
    await _require_target(session, target_id)
    windows = await pi.detect_pile_on(
        session,
        target_id,
        window_hours=window_hours,
        min_distinct_accounts=min_distinct_accounts,
        days=days,
    )
    return {"pile_ons": windows}


@router.get("/{target_id}/risk")
async def target_risk(
    target_id: UUID,
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Severity-weighted, recency-decayed risk score for this target."""
    await _require_target(session, target_id)
    return await pi.compute_risk_score(session, target_id, days=days)


@router.post("/{target_id}/reclassify")
async def target_reclassify(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> dict:
    """Re-run abuse detection over all of this target's crawls (after a dictionary update)."""
    await _require_target(session, target_id)
    from crawlers.pipeline import reclassify_log_comments

    log_rows = await session.execute(
        select(MonitoringLog.id).where(MonitoringLog.target_id == target_id)
    )
    log_ids = [r[0] for r in log_rows.all()]
    totals = {"logs": 0, "comments_checked": 0, "newly_flagged_abusive": 0}
    for log_id in log_ids:
        try:
            res = await reclassify_log_comments(session, log_id)
        except ValueError:
            continue
        totals["logs"] += 1
        totals["comments_checked"] += int(res.get("comments_checked", 0) or 0)
        totals["newly_flagged_abusive"] += int(res.get("newly_flagged_abusive", 0) or 0)
    return {"status": "done", **totals}


async def _evidence_rows(session: AsyncSession, target_id: UUID) -> list[dict]:
    q = (
        select(EvidenceReport, AccusedProfile.username)
        .outerjoin(AccusedProfile, EvidenceReport.accused_id == AccusedProfile.id)
        .where(EvidenceReport.target_id == target_id)
        .order_by(EvidenceReport.capture_timestamp.desc())
    )
    rows = await session.execute(q)
    out: list[dict] = []
    for ev, username in rows.all():
        out.append(
            {
                "evidence_id": ev.evidence_id,
                "offender_handle": username or "unknown",
                "comment_text": ev.comment_text,
                "severity": ev.severity_level.value if ev.severity_level else None,
                "risk_score": ev.risk_score,
                "captured_at": ev.capture_timestamp.isoformat() if ev.capture_timestamp else None,
                "screenshot_path": ev.screenshot_path,
            }
        )
    return out


@router.get("/{target_id}/evidence-export")
async def target_evidence_export(
    target_id: UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
):
    """Export a target's evidence (handle, comment, timestamp, severity, screenshot) as JSON or CSV."""
    target = await _require_target(session, target_id)
    rows = await _evidence_rows(session, target_id)

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "evidence_id",
                "offender_handle",
                "comment_text",
                "severity",
                "risk_score",
                "captured_at",
                "screenshot_path",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        data = buf.getvalue().encode("utf-8-sig")
        fname = f"evidence_{target.username}.csv"
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    return {
        "target_id": str(target_id),
        "target_username": target.username,
        "platform": target.platform.value,
        "exported_count": len(rows),
        "evidence": rows,
    }
