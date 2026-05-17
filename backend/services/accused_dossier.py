"""Aggregate accused identity and evidence across platforms for dossier reports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ai.risk_scoring import composite_risk_score
from database.models import AccusedProfile, CrawledComment, EvidenceReport, TargetAccount
from osint.permaliinks import build_comment_permalink


async def find_accused_profiles_by_username(
    session: AsyncSession,
    username: str,
) -> list[AccusedProfile]:
    """All platform profiles sharing the same handle (case-insensitive)."""
    normalized = username.lstrip("@").strip().lower()
    if not normalized:
        return []
    result = await session.execute(
        select(AccusedProfile)
        .where(func.lower(AccusedProfile.username) == normalized)
        .order_by(AccusedProfile.platform, AccusedProfile.last_seen_at.desc())
    )
    return list(result.scalars().all())


async def build_accused_dossier(
    session: AsyncSession,
    username: str,
) -> Optional[dict[str, Any]]:
    """
    Build a cross-platform dossier for one accused person (same username on multiple networks).
    Returns None if no accused profiles exist.
    """
    profiles = await find_accused_profiles_by_username(session, username)
    if not profiles:
        return None

    accused_ids = [p.id for p in profiles]
    Target = aliased(TargetAccount)

    Comment = aliased(CrawledComment)
    evidence_rows = await session.execute(
        select(EvidenceReport, Target.username.label("target_username"), Comment)
        .outerjoin(Target, EvidenceReport.target_id == Target.id)
        .outerjoin(Comment, EvidenceReport.comment_id == Comment.id)
        .where(EvidenceReport.accused_id.in_(accused_ids))
        .order_by(EvidenceReport.capture_timestamp.desc())
    )

    evidence_items: list[dict[str, Any]] = []
    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    platform_evidence: dict[str, int] = {}
    targets_affected: set[str] = set()
    max_risk = 0
    escalated = 0

    posts_map: dict[str, list[dict[str, Any]]] = {}
    canonical = profiles[0].username

    for row, target_username, comment in evidence_rows.all():
        sev = row.severity_level.value
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        plat = row.platform.value
        platform_evidence[plat] = platform_evidence.get(plat, 0) + 1
        if target_username:
            targets_affected.add(target_username)
        max_risk = max(max_risk, row.risk_score)
        if row.is_escalated:
            escalated += 1
        permalink = row.permalink_snapshot or {}
        comment_url = row.comment_url or (comment.comment_url if comment else None)
        post_id = row.post_id or (comment.post_id if comment else None)
        comment_id = row.platform_comment_id or (comment.comment_id if comment else None)
        accused_u = next(
            (p.username for p in profiles if p.id == row.accused_id),
            canonical,
        )
        direct_link = permalink.get("direct_comment_link") or comment_url
        if not direct_link and comment:
            direct_link = build_comment_permalink(
                plat,
                username=accused_u,
                post_id=post_id or "",
                comment_id=comment_id or "",
                post_url=row.post_url or "",
                comment_url=comment_url,
            )

        ev_item = {
            "evidence_id": row.evidence_id,
            "platform": plat,
            "severity": sev,
            "risk_score": row.risk_score,
            "target_username": target_username,
            "comment_text": row.comment_text,
            "comment_posted_at": row.comment_timestamp.isoformat()
            if row.comment_timestamp
            else None,
            "evidence_captured_at": row.capture_timestamp.isoformat()
            if row.capture_timestamp
            else None,
            "post_url": row.post_url,
            "comment_url": comment_url,
            "direct_comment_link": direct_link,
            "post_id": post_id,
            "comment_id": comment_id,
            "permalink_snapshot": permalink,
            "screenshot_path": row.screenshot_path,
            "screenshot_hash": row.screenshot_hash,
            "is_escalated": row.is_escalated,
            "accused_id": str(row.accused_id) if row.accused_id else None,
            "deletion_resilient": True,
        }
        evidence_items.append(ev_item)

        post_key = row.post_url or post_id or "unknown"
        posts_map.setdefault(post_key, []).append(
            {
                "post_url": row.post_url,
                "post_id": post_id,
                "platform": plat,
                "evidence_count": 1,
            }
        )

    profile_summaries = [
        {
            "id": str(p.id),
            "platform": p.platform.value,
            "username": p.username,
            "display_name": p.display_name,
            "bio": getattr(p, "bio", None),
            "avatar_url": p.avatar_url,
            "avatar_hash": getattr(p, "avatar_hash", None),
            "profile_url": p.profile_url,
            "total_incidents": p.total_incidents,
            "critical_count": p.critical_count,
            "high_count": p.high_count,
            "max_risk_score": p.max_risk_score,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "inferred_region": p.inferred_region,
            "first_seen_at": p.first_seen_at.isoformat() if p.first_seen_at else None,
            "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
        }
        for p in profiles
    ]

    osint_data = None
    for p in profiles:
        if getattr(p, "osint_data", None):
            osint_data = p.osint_data
            break

    affected_posts = []
    for key, items in posts_map.items():
        affected_posts.append(
            {
                "post_url": items[0].get("post_url"),
                "post_id": items[0].get("post_id"),
                "platform": items[0].get("platform"),
                "evidence_on_post": len(items),
            }
        )
    platforms = sorted({p.platform.value for p in profiles})
    composite = composite_risk_score(
        max_risk=max_risk,
        critical_count=severity_counts.get("CRITICAL", 0),
        high_count=severity_counts.get("HIGH", 0),
        platform_count=len(platforms),
        evidence_count=len(evidence_items),
    )

    return {
        "username": canonical,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform_count": len(platforms),
        "platforms": platforms,
        "profiles": profile_summaries,
        "osint": osint_data,
        "affected_posts": affected_posts,
        "summary": {
            "total_evidence": len(evidence_items),
            "severity_breakdown": severity_counts,
            "evidence_by_platform": platform_evidence,
            "targets_affected": sorted(targets_affected),
            "targets_affected_count": len(targets_affected),
            "max_risk_score": max_risk,
            "composite_risk_score": composite,
            "escalated_count": escalated,
            "total_incidents_reported": sum(p.total_incidents for p in profiles),
        },
        "evidence": evidence_items,
    }
