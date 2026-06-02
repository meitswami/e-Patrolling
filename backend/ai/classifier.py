"""Abuse classifier — hybrid keyword + optional ML toxicity model."""

from dataclasses import dataclass, field
from typing import List, Optional

from ai.abuse_categories import extract_abuse_categories
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
    abuse_categories: List[str] = field(default_factory=list)
    model_used: str = "keyword_v1"


def classify_comment(text: str, language_hint: Optional[str] = None) -> ClassificationResult:
    """Classify comment text using keyword rules and optional ML toxicity."""
    from ai.text_normalize import normalize_for_abuse_detection, is_predominantly_emoji

    normalized = normalize_for_abuse_detection(text)
    kw = analyze_text(text)
    if not kw.is_abusive and normalized != text.lower().strip():
        kw_norm = analyze_text(normalized)
        if kw_norm.confidence_score > kw.confidence_score:
            kw = kw_norm

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

    # Short-circuit: if the text is predominantly emoji with no keyword match,
    # ML models produce unreliable scores — skip them entirely to avoid false positives
    # like "God bless you ❤️❤️❤️" being scored Risk 99.
    emoji_dominant = is_predominantly_emoji(text)
    keyword_clean = not kw.is_abusive and not kw.matched_keywords

    if emoji_dominant and keyword_clean:
        return ClassificationResult(
            is_abusive=False,
            confidence_score=0.0,
            toxicity_score=0.0,
            severity_level=severity_from_score(0.0),
            risk_score=0,
            severity_score=0,
            detected_language=lang,
            matched_keywords=[],
            abuse_categories=[],
            model_used="keyword_v1_emoji_safe",
        )

    ml_score = score_toxicity(text) if use_ml else None
    api_score = score_via_inference_api(text) if use_hf else None

    indic_score = None
    use_indic = settings.USE_INDICBERT or use_ml
    if use_indic and lang in (LanguageType.HINDI, LanguageType.HINGLISH, LanguageType.UNKNOWN):
        indic_score = score_indic_abuse(text) or score_indic_abuse(normalized)

    combined = kw.confidence_score
    model_used = "keyword_v1"
    scores = [s for s in (ml_score, indic_score, api_score) if s is not None]

    if scores:
        if keyword_clean:
            # No keyword evidence — require a much higher ML consensus before
            # overriding the clean keyword verdict (prevents emoji/benign-phrase
            # false positives from single-model misfires).
            # All available ML scores must agree above 0.90.
            ml_override_threshold = 0.90
            if all(s >= ml_override_threshold for s in scores):
                combined = max(scores)
            # else keep combined = 0.0 (keyword verdict)
        else:
            # Keywords already flagged something — ML can push score higher.
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
    # Flag abusive if keywords matched OR combined score clears threshold (ML optional)
    is_abusive = kw.is_abusive or combined >= threshold or (
        not keyword_clean and any(s >= max(0.5, threshold - 0.1) for s in scores)
    )

    flags = kw.flags
    if ml_score and ml_score >= 0.7 and not flags:
        flags["ml_toxic"] = True

    matched = kw.matched_keywords + (["ml_toxic"] if ml_score and ml_score >= 0.65 else [])
    # hate_speech from ML alone requires both keyword evidence AND a very high score,
    # or multi-model consensus at 0.95+. Prevents benign emoji comments being labelled.
    ml_hate_speech = (
        bool(ml_score and ml_score >= 0.95)
        and not keyword_clean
    )
    categories = extract_abuse_categories(
        matched_keywords=matched,
        is_sexual_harassment=flags.get("sexual_harassment", False),
        is_rape_threat=flags.get("rape_threat", False),
        is_stalking=flags.get("stalking", False),
        is_hate_speech=flags.get("hate_speech", False) or ml_hate_speech,
        is_threat=flags.get("threat", False),
        is_bullying=flags.get("bullying", False),
    )

    return ClassificationResult(
        is_abusive=is_abusive,
        confidence_score=combined,
        toxicity_score=max(kw.toxicity_score, ml_score or 0.0, indic_score or 0.0, api_score or 0.0),
        severity_level=severity,
        risk_score=risk,
        severity_score=risk,
        detected_language=lang,
        matched_keywords=matched,
        is_sexual_harassment=flags.get("sexual_harassment", False),
        is_rape_threat=flags.get("rape_threat", False),
        is_stalking=flags.get("stalking", False),
        is_hate_speech=flags.get("hate_speech", False) or ml_hate_speech,
        is_threat=flags.get("threat", False),
        is_bullying=flags.get("bullying", False),
        abuse_categories=categories,
        model_used=model_used,
    )
