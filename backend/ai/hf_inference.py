"""Optional Hugging Face Inference API (no local GPU download)."""

from typing import Optional

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def score_via_inference_api(text: str, model_id: Optional[str] = None) -> Optional[float]:
    """
    Call HF Inference API for toxicity scoring when HUGGINGFACE_API_TOKEN is set.
    Returns probability 0–1 or None if unavailable.
    """
    token = settings.HUGGINGFACE_API_TOKEN
    if not token or not text.strip():
        return None

    model = model_id or settings.MULTILINGUAL_TOXIC_MODEL
    try:
        import httpx

        response = httpx.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": text[:512]},
            timeout=30.0,
        )
        if response.status_code != 200:
            logger.debug("HF Inference API %s: %s", response.status_code, response.text[:200])
            return None

        data = response.json()
        if isinstance(data, list) and data:
            best = max(data, key=lambda x: x.get("score", 0))
            label = str(best.get("label", "")).lower()
            score = float(best.get("score", 0))
            if any(t in label for t in ("toxic", "hate", "offensive", "abusive")):
                return score
            if label in ("non-toxic", "neutral", "not offensive"):
                return 1.0 - score
            return score
    except Exception as exc:
        logger.debug("HF Inference API failed: %s", exc)
    return None
