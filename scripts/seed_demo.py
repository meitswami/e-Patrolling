#!/usr/bin/env python3
"""
Seed demo targets, accused profiles, evidence, and one repeat offender for UI testing.

Usage (from repo root):
  python scripts/seed_demo.py

Idempotent: skips if PAT-DEMO-001 already exists.
Run seed_db.py first if admin user is missing.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from configs.settings import settings
from database import connection as db
from database.models import (
    AccusedProfile,
    EvidenceReport,
    OffenderStatus,
    PlatformType,
    RepeatOffender,
    SeverityLevel,
    TargetAccount,
    User,
)
from utils.logger import get_logger

logger = get_logger(__name__)

DEMO_EVIDENCE_MARKER = "PAT-DEMO-001"


async def seed_demo() -> None:
    await db.init_db()
    if db.async_session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    async with db.async_session_factory() as session:
        existing = await session.execute(
            select(EvidenceReport).where(EvidenceReport.evidence_id == DEMO_EVIDENCE_MARKER)
        )
        if existing.scalar_one_or_none():
            logger.info("Demo data already present (%s); skipping", DEMO_EVIDENCE_MARKER)
            await db.close_db()
            return

        admin = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL.lower())
        )
        admin_user = admin.scalar_one_or_none()
        admin_id = admin_user.id if admin_user else None

        now = datetime.now(timezone.utc)

        targets = [
            TargetAccount(
                username="priya_sharma_official",
                display_name="Priya Sharma",
                platform=PlatformType.INSTAGRAM,
                profile_url="https://instagram.com/priya_sharma_official",
                follower_count=124_000,
                is_verified=True,
                inferred_region="Delhi NCR",
                region_confidence=0.82,
                added_by=admin_id,
                notes="Demo target — public figure",
            ),
            TargetAccount(
                username="meera_journalist",
                display_name="Meera K.",
                platform=PlatformType.TWITTER,
                profile_url="https://twitter.com/meera_journalist",
                follower_count=48_200,
                inferred_region="Mumbai",
                added_by=admin_id,
            ),
            TargetAccount(
                username="ananya_creator",
                display_name="Ananya",
                platform=PlatformType.INSTAGRAM,
                profile_url="https://instagram.com/ananya_creator",
                follower_count=89_500,
                monitoring_enabled=False,
                is_active=False,
                added_by=admin_id,
                notes="Paused monitoring (demo)",
            ),
        ]
        session.add_all(targets)
        await session.flush()

        accused = [
            AccusedProfile(
                platform=PlatformType.INSTAGRAM,
                username="troll_account_99",
                display_name="Unknown User",
                profile_url="https://instagram.com/troll_account_99",
                total_incidents=4,
                critical_count=2,
                high_count=1,
                max_risk_score=92,
                status=OffenderStatus.CONFIRMED,
                is_repeat_offender=True,
                inferred_region="Unknown",
            ),
            AccusedProfile(
                platform=PlatformType.TWITTER,
                username="harasser_x7",
                profile_url="https://twitter.com/harasser_x7",
                total_incidents=1,
                high_count=1,
                max_risk_score=78,
                status=OffenderStatus.SUSPECTED,
            ),
        ]
        session.add_all(accused)
        await session.flush()

        repeat = RepeatOffender(
            accused_id=accused[0].id,
            total_offenses=4,
            targets_harassed=2,
            platforms_used=[PlatformType.INSTAGRAM],
            critical_count=2,
            high_count=1,
            medium_count=1,
            first_offense_at=now - timedelta(days=14),
            last_offense_at=now - timedelta(hours=3),
            status=OffenderStatus.CONFIRMED,
            priority_score=88,
            flagged_by=admin_id,
        )
        session.add(repeat)

        evidence_rows = [
            (
                "PAT-DEMO-001",
                targets[0],
                accused[0],
                "Tu bahar nikal, tujhe dikha deta hoon — roz comment karunga.",
                SeverityLevel.CRITICAL,
                92,
                now - timedelta(hours=2),
            ),
            (
                "PAT-DEMO-002",
                targets[0],
                accused[0],
                "Aise kapde pehen ke attention maangti hai phir complain karti hai.",
                SeverityLevel.HIGH,
                78,
                now - timedelta(hours=5),
            ),
            (
                "PAT-DEMO-003",
                targets[1],
                accused[1],
                "Fake journalist, teri reporting band karwa dunga.",
                SeverityLevel.HIGH,
                81,
                now - timedelta(hours=8),
            ),
            (
                "PAT-DEMO-004",
                targets[1],
                None,
                "Block kar liya phir bhi tujhe dekh lunga.",
                SeverityLevel.MEDIUM,
                55,
                now - timedelta(days=2),
            ),
            (
                "PAT-DEMO-005",
                targets[0],
                accused[0],
                "Nice photo 🙂",
                SeverityLevel.LOW,
                22,
                now - timedelta(days=5),
            ),
        ]

        for eid, target, acc, text, severity, risk, created in evidence_rows:
            session.add(
                EvidenceReport(
                    evidence_id=eid,
                    target_id=target.id,
                    accused_id=acc.id if acc else None,
                    platform=target.platform,
                    post_url=f"{target.profile_url}/p/demo",
                    comment_text=text,
                    comment_timestamp=created,
                    severity_level=severity,
                    risk_score=risk,
                    created_at=created,
                    capture_timestamp=created,
                    is_escalated=severity == SeverityLevel.CRITICAL,
                    chain_of_custody={"source": "seed_demo", "version": 1},
                )
            )

        await session.commit()
        logger.info(
            "Demo seed complete: %d targets, %d accused, %d evidence, 1 repeat offender",
            len(targets),
            len(accused),
            len(evidence_rows),
        )

    await db.close_db()


def main() -> int:
    try:
        asyncio.run(seed_demo())
        return 0
    except Exception as exc:
        logger.error("Demo seed failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
