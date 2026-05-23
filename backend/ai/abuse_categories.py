"""Map classifier output to stable abuse category labels shown in the UI."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

# Order used when displaying multiple categories (matches lexicon labels)
CANONICAL_ABUSE_CATEGORIES: tuple[str, ...] = (
    "sexual_harassment",
    "rape_threat",
    "hate_speech",
    "threat",
    "stalking",
    "bullying",
)

_CATEGORY_ALIASES = {
    "ml_toxic": "hate_speech",
}


def extract_abuse_categories(
    *,
    matched_keywords: Optional[Sequence[str]] = None,
    is_sexual_harassment: bool = False,
    is_rape_threat: bool = False,
    is_stalking: bool = False,
    is_hate_speech: bool = False,
    is_threat: bool = False,
    is_bullying: bool = False,
    extra_snapshot: Optional[dict] = None,
) -> List[str]:
    """
    Return sorted category keys, e.g. ['hate_speech', 'bullying'].
    Same names as lexicon / test output: sexual_harassment, hate_speech, bullying, etc.
    """
    found: set[str] = set()

    if extra_snapshot and isinstance(extra_snapshot.get("abuse_categories"), list):
        for c in extra_snapshot["abuse_categories"]:
            if isinstance(c, str) and c.strip():
                found.add(c.strip())

    for raw in matched_keywords or []:
        label = _CATEGORY_ALIASES.get(raw, raw)
        if label in CANONICAL_ABUSE_CATEGORIES:
            found.add(label)

    flag_map = {
        "sexual_harassment": is_sexual_harassment,
        "rape_threat": is_rape_threat,
        "stalking": is_stalking,
        "hate_speech": is_hate_speech,
        "threat": is_threat,
        "bullying": is_bullying,
    }
    for key, active in flag_map.items():
        if active:
            found.add(key)

    return [c for c in CANONICAL_ABUSE_CATEGORIES if c in found]


def format_abuse_categories_label(categories: Iterable[str]) -> str:
    """e.g. 'hate_speech + bullying' for subtitles."""
    cats = list(categories)
    if not cats:
        return "abusive"
    return " + ".join(cats)


def categories_for_evidence(
    permalink_snapshot: Optional[dict] = None,
    *,
    matched_keywords: Optional[Sequence[str]] = None,
    is_sexual_harassment: bool = False,
    is_rape_threat: bool = False,
    is_stalking: bool = False,
    is_hate_speech: bool = False,
    is_threat: bool = False,
    is_bullying: bool = False,
) -> List[str]:
    """Resolve categories from stored snapshot or linked AI result."""
    return extract_abuse_categories(
        matched_keywords=matched_keywords,
        is_sexual_harassment=is_sexual_harassment,
        is_rape_threat=is_rape_threat,
        is_stalking=is_stalking,
        is_hate_speech=is_hate_speech,
        is_threat=is_threat,
        is_bullying=is_bullying,
        extra_snapshot=permalink_snapshot,
    )
