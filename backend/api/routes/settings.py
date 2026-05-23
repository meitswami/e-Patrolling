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
from services.instagram_connect import connect_instagram_via_browser, disconnect_instagram_session
from services.instagram_validate import validate_instagram_login

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


@router.post("/crawler/connect-instagram")
async def connect_instagram(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Open Instagram in a visible browser on the server machine.
    Log in manually; session cookies are saved for crawls.
    """
    result = await connect_instagram_via_browser()
    if result.get("success") and result.get("username"):
        try:
            await sys_settings.upsert_crawler_settings(
                session,
                instagram_username=result["username"],
                updated_by=current_user.id,
            )
            await session.commit()
        except Exception:
            pass
    return result


@router.post("/crawler/disconnect-instagram")
async def disconnect_instagram(
    _user: User = Depends(require_admin),
) -> dict:
    """Remove saved Instagram session cookies."""
    return await disconnect_instagram_session()


@router.get("/crawler/instagram-session")
async def get_instagram_session_status(
    _user: User = Depends(require_admin),
) -> dict:
    """Quick check: is a saved Instagram session file present?"""
    from crawlers.instagram.session_manager import InstagramSessionManager

    sessions = InstagramSessionManager()
    return {
        "session_connected": sessions.has_saved_session(),
        "username": sessions.get_connected_username(),
    }


@router.post("/crawler/validate-instagram")
@router.post("/crawler/verify-instagram-session")
async def validate_instagram_credentials(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> dict:
    """Verify saved Instagram session cookies still work."""
    if not sys_settings._loaded:
        await sys_settings.load_cache(session)
    return await validate_instagram_login()


@router.post("/crawler/validate-instagram-test")
async def validate_instagram_credentials_test(
    _body: CrawlerSettingsUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> dict:
    """Legacy alias — verifies saved session (password fields ignored)."""
    if not sys_settings._loaded:
        await sys_settings.load_cache(session)
    return await validate_instagram_login()


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
