"""Lazy HuggingFace model loading (stub until AI pipeline is implemented)."""

from utils.logger import get_logger

logger = get_logger(__name__)


async def preload_models() -> None:
    """Optional startup preload; no-op until models are wired."""
    logger.info("AI model preload skipped (PRELOAD_AI_MODELS=false or not configured)")
