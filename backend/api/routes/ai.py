"""AI engine status and configuration."""

from fastapi import APIRouter, Depends

from auth.middleware import get_current_user
from configs.settings import settings
from database.models import User
from services import system_settings as app_settings

router = APIRouter()


@router.get("/status")
async def ai_status(_user: User = Depends(get_current_user)) -> dict:
    """Which classifiers are active (for Settings UI)."""
    use_ml = app_settings.get_use_ml_classifier()
    use_hf = app_settings.get_use_hf_inference_api()
    return {
        "keyword_engine": True,
        "local_ml": use_ml,
        "multilingual_model": settings.MULTILINGUAL_TOXIC_MODEL if use_ml else None,
        "indic_model": settings.INDIC_ABUSE_MODEL if settings.USE_INDICBERT and use_ml else None,
        "hf_inference_api": use_hf,
        "hf_api_configured": bool(settings.HUGGINGFACE_API_TOKEN),
        "recommended_models": "ai_models/configs/models.json",
        "abuse_threshold": app_settings.get_abuse_confidence_threshold(),
    }
