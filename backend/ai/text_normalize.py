"""Normalize comment text before keyword/ML abuse detection (obfuscation, Hinglish)."""

import re


def normalize_for_abuse_detection(text: str) -> str:
    """Lowercase, collapse obfuscated sexual/abusive tokens for pattern matching."""
    if not text:
        return ""
    t = text.strip().lower()
    # Common obfuscations: s*x, s3x, $ex, s e x
    t = re.sub(r"s\s*[\*#@$3]\s*x", " sex", t, flags=re.IGNORECASE)
    t = re.sub(r"\bse+x\b", " sex", t)
    # Collapse extra punctuation between letters (f*a*k*e -> fake) lightly
    t = re.sub(r"([a-z])\*+([a-z])", r"\1\2", t)
    t = re.sub(r"\s+", " ", t)
    return t
