"""Backfill abuse_categories on evidence permalink snapshots."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.abuse_categories import CANONICAL_ABUSE_CATEGORIES
from ai.abuse_explanations import build_abuse_explanations
from ai.classifier import classify_comment
from api.helpers.evidence_abuse import evidence_abuse_categories, is_lexicon_match
from database.models import AIResult, EvidenceReport

logger = logging.getLogger(__name__)


async def backfill_evidence_abuse_categories(session: AsyncSession) -> dict:
    """
    Persist abuse_categories (and lexicon flag) on every evidence row.
    Uses linked AI results; falls back to re-classifying comment text when needed.
    """
    result = await session.execute(
        select(EvidenceReport, AIResult).outerjoin(
            AIResult, EvidenceReport.ai_result_id == AIResult.id
        )
    )
    rows = result.all()
    updated = 0
    total = len(rows)

    for evidence, ai_row in rows:
        categories = evidence_abuse_categories(evidence, ai_row)
        lexicon = is_lexicon_match(ai_row)

        if not categories:
            classification = classify_comment(evidence.comment_text or "")
            if classification.is_abusive:
                categories = classification.abuse_categories
                lexicon_labels = set(CANONICAL_ABUSE_CATEGORIES)
                lexicon = lexicon or any(
                    k in lexicon_labels for k in classification.matched_keywords
                )

        snap = dict(evidence.permalink_snapshot) if evidence.permalink_snapshot else {}
        prev_cats = snap.get("abuse_categories")
        prev_lex = snap.get("is_lexicon_match")

        if categories:
            snap["abuse_categories"] = categories
        snap["is_lexicon_match"] = lexicon
        explanations = build_abuse_explanations(evidence.comment_text or "", categories)
        snap["abuse_explanations"] = explanations

        prev_expl = (evidence.permalink_snapshot or {}).get("abuse_explanations")
        if (
            prev_cats != categories
            or prev_lex != lexicon
            or explanations != prev_expl
            or (categories and "abuse_categories" not in (evidence.permalink_snapshot or {}))
        ):
            evidence.permalink_snapshot = snap
            updated += 1

    await session.commit()
    logger.info("Evidence abuse category backfill: %s/%s updated", updated, total)
    return {
        "total": total,
        "updated": updated,
        "message": f"Backfilled categories and explanations on {updated} of {total} evidence record(s).",
    }
