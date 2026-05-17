"""Abuse classifier — hybrid keyword + optional ML toxicity model."""

from dataclasses import dataclass, field
from typing import List, Optional

from ai.keyword_engine import analyze_text
from ai.language_detector import detect_language
from ai.hf_inference import score_via_inference_api
from ai.model_loader import score_indic_abuse, score_toxicity
from ai.severity_engine import risk_score_from_confidence, severity_from_score
from configs.settings import settings
from database.models import LanguageType, SeverityLevel
from services import system_settings as app_settings


@dataclass
class ClassificationResult:
    is_abusive: bool
    confidence_score: float
    toxicity_score: float
    severity_level: SeverityLevel
    risk_score: int
    severity_score: int
    detected_language: LanguageType = LanguageType.UNKNOWN
    matched_keywords: List[str] = field(default_factory=list)
    is_sexual_harassment: bool = False
    is_rape_threat: bool = False
    is_stalking: bool = False
    is_hate_speech: bool = False
    is_threat: bool = False
    is_bullying: bool = False
    model_used: str = "keyword_v1"


def classify_comment(text: str, language_hint: Optional[str] = None) -> ClassificationResult:
    """Classify comment text using keyword rules and optional ML toxicity."""
    kw = analyze_text(text)

    lang = LanguageType.UNKNOWN
    if language_hint:
        try:
            lang = LanguageType(language_hint.lower())
        except ValueError:
            pass
    if lang == LanguageType.UNKNOWN:
        lang = detect_language(text).language

    threshold = app_settings.get_abuse_confidence_threshold()
    use_ml = app_settings.get_use_ml_classifier()
    use_hf = app_settings.get_use_hf_inference_api()

    ml_score = score_toxicity(text) if use_ml else None
    api_score = score_via_inference_api(text) if use_hf else None

    indic_score = None
    if use_ml and lang in (LanguageType.HINDI, LanguageType.HINGLISH, LanguageType.UNKNOWN):
        indic_score = score_indic_abuse(text)

    combined = kw.confidence_score
    model_used = "keyword_v1"
    scores = [s for s in (ml_score, indic_score, api_score) if s is not None]

    if scores:
        combined = max(kw.confidence_score, *scores)
        parts = ["keyword"]
        if ml_score is not None:
            parts.append("toxic_bert")
        if indic_score is not None:
            parts.append("indic_deberta")
        if api_score is not None:
            parts.append("hf_api")
        model_used = "hybrid_" + "_".join(parts)

    severity = severity_from_score(combined)
    risk = risk_score_from_confidence(combined)
    is_abusive = combined >= threshold and (
        kw.is_abusive
        or any(s >= threshold for s in scores)
    )

    flags = kw.flags
    if ml_score and ml_score >= 0.7 and not flags:
        flags["ml_toxic"] = True

    return ClassificationResult(
        is_abusive=is_abusive,
        confidence_score=combined,
        toxicity_score=max(kw.toxicity_score, ml_score or 0.0, indic_score or 0.0, api_score or 0.0),
        severity_level=severity,
        risk_score=risk,
        severity_score=risk,
        detected_language=lang,
        matched_keywords=kw.matched_keywords + (["ml_toxic"] if ml_score and ml_score >= 0.65 else []),
        is_sexual_harassment=flags.get("sexual_harassment", False),
        is_rape_threat=flags.get("rape_threat", False),
        is_stalking=flags.get("stalking", False),
        is_hate_speech=flags.get("hate_speech", False) or bool(ml_score and ml_score >= 0.85),
        is_threat=flags.get("threat", False),
        is_bullying=flags.get("bullying", False),
        model_used=model_used,
    )
