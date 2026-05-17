"""Bio and display-name similarity for OSINT profile linking."""

from __future__ import annotations

import re
from typing import Optional


def _tokens(text: Optional[str]) -> set[str]:
    if not text:
        return set()
    cleaned = re.sub(r"[^\w\s@#]", " ", text.lower())
    return {t for t in cleaned.split() if len(t) > 2}


def bio_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Jaccard similarity on bio tokens (0.0–1.0)."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def display_name_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    na, nb = a.strip().lower(), b.strip().lower()
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.75
    return bio_similarity(a, b)


def username_similarity(a: str, b: str) -> float:
    na, nb = a.lstrip("@").lower(), b.lstrip("@").lower()
    if na == nb:
        return 1.0
    if na.replace(".", "").replace("_", "") == nb.replace(".", "").replace("_", ""):
        return 0.9
    if na in nb or nb in na:
        return 0.7
    return 0.0
