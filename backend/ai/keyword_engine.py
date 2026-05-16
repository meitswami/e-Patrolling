"""Fast keyword / pattern matching for abuse detection (no ML required)."""

import re
from dataclasses import dataclass, field
from typing import List

# Curated lexicon — extend from ai/prompts or external file later
_ABUSE_PATTERNS: List[tuple[str, float, str]] = [
    (r"\b(rape|balatkar|balaatkar)\b", 0.95, "rape_threat"),
    (r"\b(mar\s*dal|maar\s*dal|kill\s*you|kill\s*her)\b", 0.9, "threat"),
    (r"\b(bahar\s*aa|nikal\s*ke|dekh\s*lunga|dekh\s*lunga)\b", 0.75, "stalking"),
    (r"\b(kapde|kapdon|attention\s*maang)\b", 0.7, "sexual_harassment"),
    (r"\b(fake\s*influencer|paid\s*pr|jhooth)\b", 0.55, "bullying"),
    (r"\b(report\s*kar|police\s*mein|complain)\b", 0.5, "threat"),
    (r"\b(block\s*kar|phir\s*bhi)\b", 0.65, "stalking"),
    (r"\b(sabak|sikhaunga|sikhaunga)\b", 0.72, "threat"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE), score, label) for p, score, label in _ABUSE_PATTERNS]


@dataclass
class KeywordMatchResult:
    is_abusive: bool = False
    confidence_score: float = 0.0
    toxicity_score: float = 0.0
    matched_keywords: List[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)

    @property
    def max_score(self) -> float:
        return self.confidence_score


def analyze_text(text: str) -> KeywordMatchResult:
    """Return abuse signals from keyword patterns."""
    if not text or len(text.strip()) < 3:
        return KeywordMatchResult()

    matched: List[str] = []
    flags: dict[str, bool] = {}
    max_score = 0.0

    for pattern, score, label in _COMPILED:
        if pattern.search(text):
            matched.append(label)
            flags[label] = True
            max_score = max(max_score, score)

    return KeywordMatchResult(
        is_abusive=max_score >= 0.5,
        confidence_score=max_score,
        toxicity_score=max_score,
        matched_keywords=matched,
        flags=flags,
    )
