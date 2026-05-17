"""Scheduled weekly evidence CSV export to disk."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from configs.settings import settings
from database.models import AccusedProfile, EvidenceReport, TargetAccount


async def run_weekly_evidence_export(session: AsyncSession) -> Optional[Path]:
    """Export recent evidence to exports/ and return the file path."""
    Target = aliased(TargetAccount)
    Accused = aliased(AccusedProfile)

    result = await session.execute(
        select(
            EvidenceReport,
            Target.username.label("target_username"),
            Accused.username.label("accused_username"),
        )
        .outerjoin(Target, EvidenceReport.target_id == Target.id)
        .outerjoin(Accused, EvidenceReport.accused_id == Accused.id)
        .order_by(EvidenceReport.created_at.desc())
        .limit(5000)
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Evidence ID",
            "Platform",
            "Severity",
            "Risk Score",
            "Target",
            "Accused",
            "Comment",
            "Captured At",
        ]
    )
    for row, target_u, accused_u in result.all():
        writer.writerow(
            [
                row.evidence_id,
                row.platform.value,
                row.severity_level.value,
                row.risk_score,
                target_u or "",
                accused_u or "",
                (row.comment_text or "")[:500],
                row.capture_timestamp.isoformat() if row.capture_timestamp else "",
            ]
        )

    settings.EXPORTS_PATH.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    path = settings.EXPORTS_PATH / f"weekly_evidence_{stamp}_{uuid4().hex[:6]}.csv"
    path.write_bytes(buffer.getvalue().encode("utf-8-sig"))
    return path
