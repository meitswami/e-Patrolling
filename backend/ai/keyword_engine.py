"""Fast keyword / pattern matching for abuse detection (no ML required)."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from ai.text_normalize import normalize_for_abuse_detection
from utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_PATTERNS: List[tuple[str, float, str]] = [
    (r"\b(rape|balatkar|balaatkar)\b", 0.95, "rape_threat"),
    (r"\b(mar\s*dal|maar\s*dal|kill\s*you|kill\s*her)\b", 0.9, "threat"),
    (r"\b(bahar\s*aa|nikal\s*ke|dekh\s*lunga|dekh\s*lunga)\b", 0.75, "stalking"),
    (r"\b(kapde|kapdon|attention\s*maang)\b", 0.7, "sexual_harassment"),
    (r"\b(fake\s*influencer|paid\s*pr|jhooth)\b", 0.55, "bullying"),
    (r"\b(report\s*kar|police\s*mein|complain)\b", 0.5, "threat"),
    (r"\b(block\s*kar|phir\s*bhi)\b", 0.65, "stalking"),
    (r"\b(sabak|sikhaunga|sikhaunga)\b", 0.72, "threat"),
]

_LEXICON_PATH = Path(__file__).resolve().parents[2] / "ai_models" / "configs" / "abuse_lexicon.json"


def _load_patterns() -> List[tuple[str, float, str]]:
    if not _LEXICON_PATH.is_file():
        return _DEFAULT_PATTERNS
    try:
        data = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
        patterns = []
        for row in data.get("patterns", []):
            patterns.append((row["regex"], float(row["score"]), row["label"]))
        if patterns:
            logger.info("Loaded %d abuse patterns from lexicon", len(patterns))
            return patterns
    except (json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("Lexicon load failed, using defaults: %s", exc)
    return _DEFAULT_PATTERNS


_COMPILED: List[Tuple[re.Pattern, float, str]] = [
    (re.compile(p, re.IGNORECASE), score, label) for p, score, label in _load_patterns()
]


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
    if not text or len(text.strip()) < 2:
        return KeywordMatchResult()

    normalized = normalize_for_abuse_detection(text)
    search_text = f"{text} {normalized}"

    matched: List[str] = []
    flags: dict[str, bool] = {}
    max_score = 0.0

    for pattern, score, label in _COMPILED:
        if pattern.search(search_text):
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
