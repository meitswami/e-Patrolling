"""Normalize comment text before keyword/ML abuse detection (obfuscation, Hinglish)."""

import re

# Common deliberate misspellings / leetspeak for English profanity
_PROFANITY_REPLACEMENTS = (
    (r"\b(fcuk|fuk|phuck|fuc)\b", "fuck"),
    (r"\ba+s+h+o+l+e+\b", "asshole"),
    (r"\bc+u+n+t+\b", "cunt"),
    (r"\bd+i+c+k+\b", "dick"),
    (r"\bp+u+s+s+y+\b", "pussy"),
    (r"\bb+a+s+t+a+r+d+\b", "bastard"),
)


def normalize_for_abuse_detection(text: str) -> str:
    """Lowercase, collapse obfuscated sexual/abusive tokens for pattern matching."""
    if not text:
        return ""
    t = text.strip().lower()
    # Sexual obfuscation: s*x, s3x, $ex, s e x
    t = re.sub(r"s\s*[\*#@$3]\s*x", " sex", t, flags=re.IGNORECASE)
    t = re.sub(r"\bse+x+\b", " sex", t)
    # f-word obfuscation (apply before generic symbol collapse)
    t = re.sub(r"\bf[\*#@$!1]+u?[\*#@$!1]*c?[\*#@$!1]*k\b", "fuck", t, flags=re.IGNORECASE)
    t = re.sub(r"\bf[\*#@$!1]+c?k\b", "fuck", t, flags=re.IGNORECASE)
    t = re.sub(r"\bf\s*u\s*c\s*k\b", "fuck", t, flags=re.IGNORECASE)
    t = re.sub(r"\bsh[\*#!1@$]+t\b", "shit", t, flags=re.IGNORECASE)
    t = re.sub(r"\bb[\*#!1@$]+tch\b", "bitch", t, flags=re.IGNORECASE)
    # Collapse punctuation between letters (f*u*c*k -> fuck)
    t = re.sub(r"([a-z])[\*#@$!1]+([a-z])", r"\1\2", t)
    for pattern, replacement in _PROFANITY_REPLACEMENTS:
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t
