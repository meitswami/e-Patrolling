"""Detect Hindi, English, Hinglish, or unknown from comment text."""

import re
from dataclasses import dataclass
from typing import Optional

from database.models import LanguageType

# Devanagari block
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
# Common Hinglish tokens in Latin script
_HINGLISH_TOKENS = re.compile(
    r"\b(tu|tujhe|teri|teraa|maa|baap|nikal|dekh|lunga|karunga|sala|bekar|jhooth)\b",
    re.IGNORECASE,
)


@dataclass
class LanguageDetection:
    language: LanguageType
    confidence: float


def detect_language(text: str) -> LanguageDetection:
    if not text or len(text.strip()) < 2:
        return LanguageDetection(LanguageType.UNKNOWN, 0.0)

    has_devanagari = bool(_DEVANAGARI.search(text))
    has_latin = bool(re.search(r"[a-zA-Z]", text))
    has_hinglish = bool(_HINGLISH_TOKENS.search(text))

    if has_devanagari and has_latin:
        return LanguageDetection(LanguageType.HINGLISH, 0.85)
    if has_devanagari:
        return LanguageDetection(LanguageType.HINDI, 0.9)

    try:
        import langdetect

        code = langdetect.detect(text)
        if code == "hi":
            return LanguageDetection(
                LanguageType.HINGLISH if has_latin else LanguageType.HINDI,
                0.75,
            )
        if code == "en":
            if has_hinglish:
                return LanguageDetection(LanguageType.HINGLISH, 0.8)
            return LanguageDetection(LanguageType.ENGLISH, 0.8)
    except Exception:
        pass

    if has_hinglish:
        return LanguageDetection(LanguageType.HINGLISH, 0.7)
    if has_latin:
        return LanguageDetection(LanguageType.ENGLISH, 0.6)

    return LanguageDetection(LanguageType.UNKNOWN, 0.3)
