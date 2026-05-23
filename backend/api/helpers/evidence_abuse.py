"""Resolve abuse category labels for API responses."""

from __future__ import annotations

from typing import List, Optional

from ai.abuse_categories import CANONICAL_ABUSE_CATEGORIES, categories_for_evidence
from ai.abuse_explanations import build_abuse_explanations
from database.models import AIResult, EvidenceReport


def is_lexicon_match(
    ai_result: Optional[AIResult] = None,
    permalink_snapshot: Optional[dict] = None,
) -> bool:
    """True when lexicon/keyword engine matched (not ML-only)."""
    if ai_result and ai_result.matched_keywords:
        lexicon_labels = set(CANONICAL_ABUSE_CATEGORIES)
        if any(k in lexicon_labels for k in ai_result.matched_keywords):
            return True
    snap = permalink_snapshot or {}
    return bool(snap.get("is_lexicon_match"))


def evidence_abuse_categories(
    evidence: EvidenceReport,
    ai_result: Optional[AIResult] = None,
) -> List[str]:
    if ai_result is not None:
        return categories_for_evidence(
            evidence.permalink_snapshot,
            matched_keywords=ai_result.matched_keywords,
            is_sexual_harassment=ai_result.is_sexual_harassment,
            is_rape_threat=ai_result.is_rape_threat,
            is_stalking=ai_result.is_stalking,
            is_hate_speech=ai_result.is_hate_speech,
            is_threat=ai_result.is_threat,
            is_bullying=ai_result.is_bullying,
        )
    return categories_for_evidence(evidence.permalink_snapshot)


def apply_evidence_abuse_fields(
    item,
    evidence: EvidenceReport,
    ai_result: Optional[AIResult] = None,
) -> None:
    """Set abuse_categories, is_abusive, is_lexicon_match on API schema instances."""
    categories = evidence_abuse_categories(evidence, ai_result)
    item.abuse_categories = categories
    # Evidence rows are abusive captures; always highlight comment text.
    item.is_abusive = True
    item.is_lexicon_match = is_lexicon_match(ai_result, evidence.permalink_snapshot)
    snap = evidence.permalink_snapshot or {}
    stored = snap.get("abuse_explanations")
    if isinstance(stored, list) and stored:
        item.abuse_explanations = stored
    else:
        item.abuse_explanations = build_abuse_explanations(
            evidence.comment_text or "",
            categories,
        )
