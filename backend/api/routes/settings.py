"""Admin system settings — crawler credentials stored in database."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.settings import (
    AiSettingsResponse,
    AiSettingsUpdate,
    CrawlerSettingsResponse,
    CrawlerSettingsUpdate,
)
from auth.rbac import require_admin
from database.connection import get_session
from database.models import User
from services import system_settings as sys_settings

router = APIRouter()


@router.get("/crawler", response_model=CrawlerSettingsResponse)
async def get_crawler_settings(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> CrawlerSettingsResponse:
    """Read crawler / Instagram settings (admin only). Password is never returned."""
    if not sys_settings._loaded:
        await sys_settings.load_cache(session)
    data = await sys_settings.get_crawler_settings_public()
    return CrawlerSettingsResponse(**data)


@router.put("/crawler", response_model=CrawlerSettingsResponse)
async def update_crawler_settings(
    body: CrawlerSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> CrawlerSettingsResponse:
    """Save crawler settings to system_settings table (admin only)."""
    try:
        data = await sys_settings.upsert_crawler_settings(
            session,
            crawler_demo_mode=body.crawler_demo_mode,
            instagram_username=body.instagram_username,
            instagram_password=body.instagram_password,
            facebook_email=body.facebook_email,
            facebook_password=body.facebook_password,
            evidence_screenshot_mode=body.evidence_screenshot_mode,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return CrawlerSettingsResponse(**data)


@router.get("/ai", response_model=AiSettingsResponse)
async def get_ai_settings(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> AiSettingsResponse:
    if not sys_settings._loaded:
        await sys_settings.load_cache(session)
    data = await sys_settings.get_ai_settings_public()
    return AiSettingsResponse(**data)


@router.put("/ai", response_model=AiSettingsResponse)
async def update_ai_settings(
    body: AiSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> AiSettingsResponse:
    try:
        data = await sys_settings.upsert_ai_settings(
            session,
            use_ml_classifier=body.use_ml_classifier,
            use_hf_inference_api=body.use_hf_inference_api,
            abuse_confidence_threshold=body.abuse_confidence_threshold,
            updated_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return AiSettingsResponse(**data)
