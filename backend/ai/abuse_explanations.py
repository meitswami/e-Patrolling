"""Build human-readable explanations for detected abuse (Hinglish / lexicon context)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Sequence

from ai.text_normalize import normalize_for_abuse_detection

_GLOSSARY_PATH = (
    Path(__file__).resolve().parents[2] / "ai_models" / "configs" / "abuse_term_glossary.json"
)

CATEGORY_EXPLANATIONS: dict[str, dict[str, str]] = {
    "sexual_harassment": {
        "title": "Sexual harassment",
        "meaning_en": "Unwanted sexual comments, solicitation, or objectification — not legitimate feedback.",
        "offender_implication": "The offender treats the target as a sexual object, ignores boundaries, and may pressure, expose, or humiliate them in public.",
    },
    "rape_threat": {
        "title": "Rape threat",
        "meaning_en": "Language referencing rape or sexual violence as threat or wish of harm.",
        "offender_implication": "Aims to terrify and dominate; can constitute a serious criminal threat and deep psychological harm.",
    },
    "hate_speech": {
        "title": "Hate speech / slurs",
        "meaning_en": "Uses severe slurs (often Hindi/Hinglish: bc, bsdk, mc, etc.) or degrading attacks on identity or dignity.",
        "offender_implication": "Meant to insult, demean, and provoke — not to debate. Often invites pile-on harassment from others.",
    },
    "threat": {
        "title": "Threat",
        "meaning_en": "Threatens physical harm, death, or violent action against the target or family.",
        "offender_implication": "Intimidation and fear — signals willingness to harm or encourages others to act violently.",
    },
    "stalking": {
        "title": "Stalking / persistent harassment",
        "meaning_en": "Suggests continued unwanted contact, surveillance, or refusal to leave the target alone.",
        "offender_implication": "Control and fear — implies the offender will keep pursuing the target despite boundaries.",
    },
    "bullying": {
        "title": "Bullying / reputational attack",
        "meaning_en": "Shames, mocks, or attacks credibility (e.g. “fake”, “paid PR”, public call-outs).",
        "offender_implication": "Damages reputation and social standing; may aim to cancel sponsorships, followers, or mental well-being.",
    },
}


@dataclass
class AbuseExplanation:
    kind: str  # phrase | term | category
    title: str
    meaning_en: str
    offender_implication: str
    related_categories: List[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "meaning_en": self.meaning_en,
            "offender_implication": self.offender_implication,
            "related_categories": self.related_categories,
        }


def _load_glossary() -> tuple[list[dict], list[dict]]:
    if not _GLOSSARY_PATH.is_file():
        return [], []
    try:
        data = json.loads(_GLOSSARY_PATH.read_text(encoding="utf-8"))
        phrases = sorted(
            data.get("phrases", []),
            key=lambda p: len(p.get("detect", "")),
            reverse=True,
        )
        terms = sorted(
            data.get("terms", []),
            key=lambda t: len(t.get("detect", "")),
            reverse=True,
        )
        return phrases, terms
    except (json.JSONDecodeError, OSError):
        return [], []


def build_abuse_explanations(
    comment_text: str,
    abuse_categories: Optional[Sequence[str]] = None,
) -> List[dict[str, Any]]:
    """
    Return ordered explanations: matched phrases/terms first, then category context.
    """
    if not comment_text or not comment_text.strip():
        return []

    normalized = normalize_for_abuse_detection(comment_text)
    search_text = f"{comment_text}\n{normalized}".lower()
    categories = list(abuse_categories or [])
    cat_set = set(categories)
    out: List[AbuseExplanation] = []
    seen_ids: set[str] = set()
    covered_cats: set[str] = set()

    phrases, terms = _load_glossary()
    blocked_term_ids: set[str] = set()

    for entry in phrases:
        eid = entry.get("id", "")
        if eid in seen_ids:
            continue
        pattern = entry.get("detect")
        if not pattern:
            continue
        if re.search(pattern, search_text, re.IGNORECASE):
            seen_ids.add(eid)
            related = entry.get("categories") or []
            covered_cats.update(related)
            out.append(
                AbuseExplanation(
                    kind="phrase",
                    title=entry.get("display") or eid,
                    meaning_en=entry.get("meaning_en", ""),
                    offender_implication=entry.get("offender_implication", ""),
                    related_categories=list(related),
                )
            )
            for blocked in entry.get("also_blocks") or []:
                blocked_term_ids.add(blocked)

    for entry in terms:
        eid = entry.get("id", "")
        if eid in seen_ids or eid in blocked_term_ids:
            continue
        pattern = entry.get("detect")
        if not pattern:
            continue
        if re.search(pattern, search_text, re.IGNORECASE):
            seen_ids.add(eid)
            related = entry.get("categories") or []
            covered_cats.update(related)
            out.append(
                AbuseExplanation(
                    kind="term",
                    title=entry.get("display") or eid,
                    meaning_en=entry.get("meaning_en", ""),
                    offender_implication=entry.get("offender_implication", ""),
                    related_categories=list(related),
                )
            )

    for cat in categories:
        if cat in covered_cats:
            continue
        meta = CATEGORY_EXPLANATIONS.get(cat)
        if not meta:
            continue
        out.append(
            AbuseExplanation(
                kind="category",
                title=meta["title"],
                meaning_en=meta["meaning_en"],
                offender_implication=meta["offender_implication"],
                related_categories=[cat],
            )
        )

    # If we matched terms but categories empty, still add category notes for those term cats
    if not out and cat_set:
        for cat in categories:
            meta = CATEGORY_EXPLANATIONS.get(cat)
            if meta:
                out.append(
                    AbuseExplanation(
                        kind="category",
                        title=meta["title"],
                        meaning_en=meta["meaning_en"],
                        offender_implication=meta["offender_implication"],
                        related_categories=[cat],
                    )
                )

    return [e.to_dict() for e in out]
