"""AI engine status and configuration."""

from fastapi import APIRouter, Depends

from auth.middleware import get_current_user
from configs.settings import settings
from database.models import User

router = APIRouter()


@router.get("/status")
async def ai_status(_user: User = Depends(get_current_user)) -> dict:
    """Which classifiers are active (for Settings UI)."""
    return {
        "keyword_engine": True,
        "local_ml": settings.USE_ML_CLASSIFIER,
        "multilingual_model": settings.MULTILINGUAL_TOXIC_MODEL if settings.USE_ML_CLASSIFIER else None,
        "indic_model": settings.INDIC_ABUSE_MODEL if settings.USE_INDICBERT else None,
        "hf_inference_api": settings.USE_HF_INFERENCE_API,
        "hf_api_configured": bool(settings.HUGGINGFACE_API_TOKEN),
        "recommended_models": "ai_models/configs/models.json",
        "abuse_threshold": settings.ABUSE_CONFIDENCE_THRESHOLD,
    }
