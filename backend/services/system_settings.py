"""
Runtime system settings — DB overrides with .env fallbacks.

Sensitive values (e.g. Instagram password) are Fernet-encrypted at rest.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configs.settings import settings
from database.models import SystemSetting
from utils.logger import get_logger

logger = get_logger(__name__)

MASKED_SECRET = "********"

SETTING_KEYS = frozenset(
    {
        "crawler_demo_mode",
        "instagram_username",
        "instagram_password",
        "facebook_email",
        "facebook_password",
        "evidence_screenshot_mode",
    }
)

_cache: dict[str, str] = {}
_loaded = False


def _fernet():
    from cryptography.fernet import Fernet

    digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(cipher: str) -> str:
    return _fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")


def invalidate_cache() -> None:
    global _loaded
    _cache.clear()
    _loaded = False


async def load_cache(session: AsyncSession) -> None:
    """Load all system_settings rows into memory."""
    global _loaded
    result = await session.execute(select(SystemSetting))
    rows = result.scalars().all()
    _cache.clear()
    for row in rows:
        if row.key in SETTING_KEYS:
            _cache[row.key] = row.value
    _loaded = True
    logger.info("System settings cache loaded (%d keys)", len(_cache))


def _raw(key: str) -> Optional[str]:
    return _cache.get(key)


def get_crawler_demo_mode() -> bool:
    raw = _raw("crawler_demo_mode")
    if raw is None:
        return settings.CRAWLER_DEMO_MODE
    return raw.strip().lower() in ("1", "true", "yes", "on")


def get_instagram_username() -> Optional[str]:
    raw = _raw("instagram_username")
    if raw is not None and raw.strip():
        return raw.strip()
    return settings.INSTAGRAM_USERNAME


def get_instagram_password() -> Optional[str]:
    raw = _raw("instagram_password")
    if raw:
        try:
            return decrypt_secret(raw)
        except Exception as exc:
            logger.error("Failed to decrypt instagram_password: %s", exc)
            return settings.INSTAGRAM_PASSWORD
    return settings.INSTAGRAM_PASSWORD


def get_evidence_screenshot_mode() -> str:
    raw = _raw("evidence_screenshot_mode")
    if raw and raw.strip():
        return raw.strip().lower()
    return (settings.EVIDENCE_SCREENSHOT_MODE or "both").lower()


def instagram_credentials_configured() -> bool:
    user = get_instagram_username()
    pwd = get_instagram_password()
    return bool(user and pwd)


def has_instagram_password_in_db() -> bool:
    return bool(_raw("instagram_password"))


def get_facebook_email() -> Optional[str]:
    raw = _raw("facebook_email")
    if raw is not None and raw.strip():
        return raw.strip()
    return None


def get_facebook_password() -> Optional[str]:
    raw = _raw("facebook_password")
    if raw:
        try:
            return decrypt_secret(raw)
        except Exception as exc:
            logger.error("Failed to decrypt facebook_password: %s", exc)
            return None
    return None


def facebook_credentials_configured() -> bool:
    return bool(get_facebook_email() and get_facebook_password())


def has_facebook_password_in_db() -> bool:
    return bool(_raw("facebook_password"))


async def get_crawler_settings_public() -> dict[str, Any]:
    """Safe view for API (no plaintext password)."""
    return {
        "crawler_demo_mode": get_crawler_demo_mode(),
        "instagram_username": get_instagram_username() or "",
        "instagram_password_set": instagram_credentials_configured(),
        "instagram_password_configured_in_db": has_instagram_password_in_db(),
        "facebook_email": get_facebook_email() or "",
        "facebook_password_set": facebook_credentials_configured(),
        "facebook_password_configured_in_db": has_facebook_password_in_db(),
        "facebook_access_token_set": bool(settings.FACEBOOK_ACCESS_TOKEN),
        "threads_uses_instagram_login": True,
        "evidence_screenshot_mode": get_evidence_screenshot_mode(),
        "source": "database" if _loaded and _cache else "environment",
    }


async def upsert_crawler_settings(
    session: AsyncSession,
    *,
    crawler_demo_mode: Optional[bool] = None,
    instagram_username: Optional[str] = None,
    instagram_password: Optional[str] = None,
    facebook_email: Optional[str] = None,
    facebook_password: Optional[str] = None,
    evidence_screenshot_mode: Optional[str] = None,
    updated_by: Optional[Any] = None,
) -> dict[str, Any]:
    """Persist crawler settings; password omitted or MASKED_SECRET keeps existing."""
    updates: dict[str, str] = {}

    if crawler_demo_mode is not None:
        updates["crawler_demo_mode"] = "true" if crawler_demo_mode else "false"

    if instagram_username is not None:
        updates["instagram_username"] = instagram_username.strip()

    if instagram_password is not None:
        pwd = instagram_password.strip()
        if pwd and pwd != MASKED_SECRET:
            updates["instagram_password"] = encrypt_secret(pwd)

    if facebook_email is not None:
        updates["facebook_email"] = facebook_email.strip()

    if facebook_password is not None:
        pwd = facebook_password.strip()
        if pwd and pwd != MASKED_SECRET:
            updates["facebook_password"] = encrypt_secret(pwd)

    if evidence_screenshot_mode is not None:
        mode = evidence_screenshot_mode.strip().lower()
        if mode not in ("pillow", "playwright", "both"):
            raise ValueError("evidence_screenshot_mode must be pillow, playwright, or both")
        updates["evidence_screenshot_mode"] = mode

    for key, value in updates.items():
        result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
        row = result.scalar_one_or_none()
        is_secret = key in ("instagram_password", "facebook_password")
        if row:
            row.value = value
            row.is_secret = is_secret
            if updated_by:
                row.updated_by = updated_by
        else:
            session.add(
                SystemSetting(
                    key=key,
                    value=value,
                    is_secret=is_secret,
                    updated_by=updated_by,
                )
            )
        _cache[key] = value

    await session.flush()
    global _loaded
    _loaded = True
    return await get_crawler_settings_public()
