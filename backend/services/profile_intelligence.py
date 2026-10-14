"""Profile Intelligence services.

Three capabilities, all grounded in data the platform already collects on a
target's own posts:

1. record_profile_observation / get_profile_knowledge
   Track the MONITORED account's own public profile over time and keep a
   "was X, now Y" change history (name / bio / verification / affiliation).

2. top_offenders / detect_pile_on
   Handle-level repeat-offender ranking and coordinated pile-on detection.
   Aggregates over existing evidence — no de-anonymizing of commenters.

3. compute_risk_score
   A severity-weighted, recency-decayed risk number per target.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AccusedProfile, EvidenceReport, SeverityLevel
from database.models_intelligence import TargetProfileChange, TargetProfileKnowledge

# Fields mirrored into the knowledge snapshot on every observation.
_SNAPSHOT_FIELDS = (
    "display_name",
    "bio",
    "follower_count",
    "following_count",
    "posts_count",
    "is_verified",
    "is_private",
)
# Identity fields whose changes are worth a history entry. Follower/engagement
# counts churn constantly, so they update the snapshot but are not logged as
# "changes" — only meaningful identity shifts are (name, bio, verification).
_CHANGE_TRACKED = ("display_name", "bio", "is_verified", "is_private")

_SEVERITY_WEIGHT = {
    SeverityLevel.LOW: 1.0,
    SeverityLevel.MEDIUM: 3.0,
    SeverityLevel.HIGH: 7.0,
    SeverityLevel.CRITICAL: 15.0,
}


def _norm(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


async def record_profile_observation(
    session: AsyncSession,
    target_id: UUID,
    observed: dict[str, Any],
    *,
    source: str = "crawl",
) -> list[dict[str, Any]]:
    """
    Compare a freshly observed public profile against what we last knew and
    record any identity changes. Returns the list of change dicts written
    (empty on the first observation, which just establishes the baseline).
    """
    row = await session.get(TargetProfileKnowledge, target_id)
    now = datetime.now(timezone.utc)
    changes: list[dict[str, Any]] = []

    if row is None:
        row = TargetProfileKnowledge(target_id=target_id)
        for f in _SNAPSHOT_FIELDS:
            if f in observed:
                setattr(row, f, observed[f])
        row.first_seen_at = now
        row.last_updated_at = now
        session.add(row)
        await session.flush()
        return changes

    for f in _SNAPSHOT_FIELDS:
        if f not in observed:
            continue
        new_val = observed[f]
        if new_val is None:
            continue  # missing reading — don't erase what we know
        old_val = getattr(row, f)
        if f in _CHANGE_TRACKED and _norm(old_val) != _norm(new_val):
            change = TargetProfileChange(
                target_id=target_id,
                field=f,
                old_value=_norm(old_val),
                new_value=_norm(new_val),
                source=source,
            )
            session.add(change)
            changes.append(
                {"field": f, "old_value": _norm(old_val), "new_value": _norm(new_val)}
            )
        setattr(row, f, new_val)

    row.last_updated_at = now
    await session.flush()
    return changes


async def get_profile_knowledge(
    session: AsyncSession, target_id: UUID, *, history_limit: int = 50
) -> dict[str, Any]:
    """Return the current known profile plus recent change history."""
    row = await session.get(TargetProfileKnowledge, target_id)
    hist = await session.execute(
        select(TargetProfileChange)
        .where(TargetProfileChange.target_id == target_id)
        .order_by(TargetProfileChange.changed_at.desc())
        .limit(history_limit)
    )
    changes = [
        {
            "field": c.field,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "source": c.source,
            "changed_at": c.changed_at.isoformat() if c.changed_at else None,
        }
        for c in hist.scalars().all()
    ]
    if row is None:
        return {"known": False, "profile": None, "changes": changes}
    return {
        "known": True,
        "profile": {
            "display_name": row.display_name,
            "bio": row.bio,
            "follower_count": row.follower_count,
            "following_count": row.following_count,
            "posts_count": row.posts_count,
            "is_verified": row.is_verified,
            "is_private": row.is_private,
            "public_facts": row.public_facts or {},
            "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            "last_updated_at": row.last_updated_at.isoformat() if row.last_updated_at else None,
        },
        "changes": changes,
    }


async def top_offenders(
    session: AsyncSession, target_id: UUID, *, limit: int = 20, days: int = 365
) -> list[dict[str, Any]]:
    """Handles that abuse this target most, ranked by incident count then risk."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = (
        select(
            EvidenceReport.accused_id,
            AccusedProfile.username,
            func.count().label("incidents"),
            func.max(EvidenceReport.risk_score).label("max_risk"),
            func.min(EvidenceReport.capture_timestamp).label("first_seen"),
            func.max(EvidenceReport.capture_timestamp).label("last_seen"),
        )
        .outerjoin(AccusedProfile, EvidenceReport.accused_id == AccusedProfile.id)
        .where(
            EvidenceReport.target_id == target_id,
            EvidenceReport.capture_timestamp >= since,
        )
        .group_by(EvidenceReport.accused_id, AccusedProfile.username)
        .order_by(func.count().desc(), func.max(EvidenceReport.risk_score).desc())
        .limit(limit)
    )
    rows = await session.execute(q)
    out: list[dict[str, Any]] = []
    for accused_id, username, incidents, max_risk, first_seen, last_seen in rows.all():
        out.append(
            {
                "accused_id": str(accused_id) if accused_id else None,
                "username": username or "unknown",
                "incidents": int(incidents or 0),
                "max_risk_score": int(max_risk or 0),
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
            }
        )
    return out


async def detect_pile_on(
    session: AsyncSession,
    target_id: UUID,
    *,
    window_hours: int = 6,
    min_distinct_accounts: int = 5,
    days: int = 30,
) -> list[dict[str, Any]]:
    """
    Flag coordinated pile-ons: fixed time buckets of `window_hours` in which
    many DISTINCT accounts abuse the same target. Bucketing is done in Python
    to stay independent of any Postgres-version-specific date functions.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await session.execute(
            select(
                EvidenceReport.accused_id,
                EvidenceReport.capture_timestamp,
                EvidenceReport.risk_score,
            ).where(
                EvidenceReport.target_id == target_id,
                EvidenceReport.capture_timestamp >= since,
            )
        )
    ).all()

    win = max(1, window_hours) * 3600
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
    buckets: dict[int, dict[str, Any]] = {}
    for accused_id, ts, risk in rows:
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        idx = int((ts - epoch).total_seconds() // win)
        b = buckets.setdefault(
            idx, {"accounts": set(), "comments": 0, "max_risk": 0}
        )
        b["accounts"].add(str(accused_id) if accused_id else f"anon:{ts.isoformat()}")
        b["comments"] += 1
        b["max_risk"] = max(b["max_risk"], int(risk or 0))

    out: list[dict[str, Any]] = []
    for idx, b in buckets.items():
        if len(b["accounts"]) < min_distinct_accounts:
            continue
        start = epoch + timedelta(seconds=idx * win)
        out.append(
            {
                "window_start": start.isoformat(),
                "window_hours": window_hours,
                "distinct_accounts": len(b["accounts"]),
                "comments": b["comments"],
                "max_risk_score": b["max_risk"],
            }
        )
    out.sort(key=lambda r: r["window_start"], reverse=True)
    return out


async def compute_risk_score(
    session: AsyncSession, target_id: UUID, *, days: int = 30, half_life_days: float = 7.0
) -> dict[str, Any]:
    """
    Severity-weighted, recency-decayed risk score in [0, 100] for a target.
    Recent CRITICAL abuse dominates; old LOW abuse barely registers.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = select(
        EvidenceReport.severity_level, EvidenceReport.capture_timestamp
    ).where(
        EvidenceReport.target_id == target_id,
        EvidenceReport.capture_timestamp >= since,
    )
    rows = (await session.execute(q)).all()
    now = datetime.now(timezone.utc)
    raw = 0.0
    counts = {s.value: 0 for s in SeverityLevel}
    for severity, ts in rows:
        weight = _SEVERITY_WEIGHT.get(severity, 1.0)
        if ts is not None:
            age_days = max((now - ts).total_seconds() / 86400.0, 0.0)
            decay = 0.5 ** (age_days / half_life_days)
        else:
            decay = 1.0
        raw += weight * decay
        if severity is not None:
            counts[severity.value] = counts.get(severity.value, 0) + 1
    # Saturating map: raw 0 -> 0, grows toward 100. K controls how fast.
    k = 40.0
    score = round(100.0 * (1.0 - math.exp(-raw / k)), 1)
    band = "low"
    if score >= 75:
        band = "critical"
    elif score >= 50:
        band = "high"
    elif score >= 25:
        band = "elevated"
    return {
        "risk_score": score,
        "band": band,
        "window_days": days,
        "incident_counts": counts,
        "total_incidents": len(rows),
    }
