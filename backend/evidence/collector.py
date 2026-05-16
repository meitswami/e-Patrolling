"""Create evidence reports from classified abusive comments."""

import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.classifier import ClassificationResult
from database.models import AccusedProfile, EvidenceReport, PlatformType
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_evidence_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = secrets.token_hex(3).upper()
    return f"EVD-{stamp}-{suffix}"


async def get_or_create_accused(
    session: AsyncSession,
    *,
    platform: PlatformType,
    username: str,
    profile_url: str,
    display_name: Optional[str] = None,
) -> AccusedProfile:
    result = await session.execute(
        select(AccusedProfile).where(
            AccusedProfile.platform == platform,
            AccusedProfile.username == username,
        )
    )
    accused = result.scalar_one_or_none()
    if accused:
        return accused

    accused = AccusedProfile(
        platform=platform,
        username=username,
        display_name=display_name,
        profile_url=profile_url,
    )
    session.add(accused)
    await session.flush()
    return accused


async def create_evidence_from_classification(
    session: AsyncSession,
    *,
    comment_id: UUID,
    ai_result_id: UUID,
    target_id: UUID,
    accused_id: UUID,
    platform: PlatformType,
    post_url: Optional[str],
    comment_text: str,
    comment_timestamp: Optional[datetime],
    classification: ClassificationResult,
    screenshot_path: Optional[str] = None,
    evidence_id: Optional[str] = None,
) -> EvidenceReport:
    evidence = EvidenceReport(
        evidence_id=evidence_id or generate_evidence_id(),
        comment_id=comment_id,
        ai_result_id=ai_result_id,
        target_id=target_id,
        accused_id=accused_id,
        platform=platform,
        post_url=post_url,
        comment_text=comment_text,
        comment_timestamp=comment_timestamp,
        severity_level=classification.severity_level,
        risk_score=classification.risk_score,
        screenshot_path=screenshot_path,
        chain_of_custody={
            "collector": "evidence.collector",
            "model": classification.model_used,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        is_escalated=classification.severity_level.value == "CRITICAL",
    )
    session.add(evidence)
    await session.flush()
    logger.info("Evidence created: %s (risk=%s)", evidence.evidence_id, evidence.risk_score)
    return evidence
