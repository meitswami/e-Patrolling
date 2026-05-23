"""Lazy HuggingFace model loading with graceful fallback."""

from typing import Any, Optional

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_toxic_pipeline: Any = None
_indic_pipeline: Any = None
_load_failed = False
_indic_load_failed = False


def _load_toxic_pipeline() -> Any:
    global _toxic_pipeline, _load_failed
    if _load_failed:
        return None
    if _toxic_pipeline is not None:
        return _toxic_pipeline
    try:
        from transformers import pipeline

        device = 0 if settings.USE_GPU else -1
        model_id = settings.MULTILINGUAL_TOXIC_MODEL if settings.USE_MULTILINGUAL_TOXIC else settings.TOXIC_BERT_MODEL
        _toxic_pipeline = pipeline(
            "text-classification",
            model=model_id,
            device=device,
            truncation=True,
            max_length=512,
        )
        logger.info("Loaded toxicity model: %s", settings.TOXIC_BERT_MODEL)
        return _toxic_pipeline
    except Exception as exc:
        _load_failed = True
        logger.warning("ML model load failed (keyword fallback only): %s", exc)
        return None


def _load_indic_pipeline() -> Any:
    global _indic_pipeline, _indic_load_failed
    if _indic_load_failed:
        return None
    if _indic_pipeline is not None:
        return _indic_pipeline
    try:
        from transformers import pipeline

        device = 0 if settings.USE_GPU else -1
        _indic_pipeline = pipeline(
            "text-classification",
            model=settings.INDIC_ABUSE_MODEL,
            device=device,
            truncation=True,
            max_length=256,
        )
        logger.info("Loaded Indic abuse model: %s", settings.INDIC_ABUSE_MODEL)
        return _indic_pipeline
    except Exception as exc:
        _indic_load_failed = True
        logger.warning("IndicBERT/DeBERTa load failed: %s", exc)
        return None


async def preload_models() -> None:
    """Optional startup preload."""
    if settings.USE_ML_CLASSIFIER:
        _load_toxic_pipeline()
    if settings.USE_INDICBERT:
        _load_indic_pipeline()
    if not settings.USE_ML_CLASSIFIER and not settings.USE_INDICBERT:
        logger.info("ML models disabled — keyword classifier only")


def score_toxicity(text: str) -> Optional[float]:
    """
    Return toxicity probability 0–1 from toxic-bert, or None if unavailable.
  Label 'toxic' score is used when model returns multi-label output.
    """
    if not settings.USE_ML_CLASSIFIER or not text.strip():
        return None

    pipe = _load_toxic_pipeline()
    if pipe is None:
        return None

    try:
        results = pipe(text[:512])
        if not results:
            return None
        # toxic-bert: [{'label': 'toxic', 'score': 0.9}] or similar
        best = max(results, key=lambda r: r.get("score", 0))
        label = str(best.get("label", "")).lower()
        score = float(best.get("score", 0))
        if "toxic" in label or "hate" in label or "offensive" in label:
            return score
        if label in ("non-toxic", "neutral", "not offensive"):
            return 1.0 - score
        return score
    except Exception as exc:
        logger.debug("Toxicity scoring failed: %s", exc)
        return None


def score_indic_abuse(text: str) -> Optional[float]:
    """Hindi/Hinglish abuse score via dehatebert-mono-indic (when enabled)."""
    if not (settings.USE_INDICBERT or settings.USE_ML_CLASSIFIER) or not text.strip():
        return None

    pipe = _load_indic_pipeline()
    if pipe is None:
        return None

    try:
        results = pipe(text[:256])
        if not results:
            return None
        best = max(results, key=lambda r: r.get("score", 0))
        label = str(best.get("label", "")).lower()
        score = float(best.get("score", 0))
        if any(x in label for x in ("hate", "offensive", "abusive", "toxic")):
            return score
        if label in ("normal", "non-hate", "not offensive"):
            return 1.0 - score
        return score
    except Exception as exc:
        logger.debug("Indic scoring failed: %s", exc)
        return None
