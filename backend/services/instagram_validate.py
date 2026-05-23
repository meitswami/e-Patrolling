"""Verify saved Instagram session cookies (no password login)."""

from __future__ import annotations

import asyncio
from typing import Optional

from crawlers.instagram.session_manager import InstagramSessionManager
from utils.logger import get_logger

logger = get_logger(__name__)


def _format_error(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text
    return f"{type(exc).__name__} (no detail — try: python -m playwright install chromium)"


async def _chromium_available() -> tuple[bool, str]:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False, "Playwright is not installed. Run: pip install playwright"

    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.launch(headless=True, timeout=60000)
        await browser.close()
        return True, ""
    except Exception as exc:
        hint = (
            "Install Chromium for Playwright: open a terminal in the backend folder and run "
            "`python -m playwright install chromium`"
        )
        return False, f"{_format_error(exc)}. {hint}"
    finally:
        await playwright.stop()


async def validate_instagram_login(
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> dict:
    """
    Check that a saved Instagram session file exists and still works.
    Password args are ignored (legacy API compatibility).
    """
    sessions = InstagramSessionManager()
    connected_user = sessions.get_connected_username() or username

    if not sessions.has_saved_session():
        return {
            "success": False,
            "message": (
                "No Instagram session saved. In Settings, click Connect Instagram and log in "
                "in the browser window that opens."
            ),
            "username": connected_user,
        }

    ok, chromium_msg = await _chromium_available()
    if not ok:
        return {
            "success": False,
            "message": f"Browser setup failed: {chromium_msg}",
            "username": connected_user,
        }

    playwright = None
    browser = None
    context = None
    page = None
    try:
        from playwright.async_api import async_playwright

        storage = sessions.load_storage_state()
        if not storage:
            return {
                "success": False,
                "message": "Session file is invalid. Connect Instagram again.",
                "username": connected_user,
            }

        playwright = await async_playwright().start()
        for channel in ("chrome", "msedge", None):
            try:
                if channel:
                    browser = await playwright.chromium.launch(channel=channel, headless=True)
                else:
                    browser = await playwright.chromium.launch(headless=True)
                break
            except Exception:
                continue
        if not browser:
            raise RuntimeError("Could not launch browser for session check")

        context = await browser.new_context(storage_state=storage)
        page = await context.new_page()
        await page.goto("https://www.instagram.com/", wait_until="load", timeout=90000)
        await asyncio.sleep(2)

        url = (page.url or "").lower()
        if "accounts/login" in url or "/login" in url:
            sessions.clear_session()
            return {
                "success": False,
                "message": "Saved session expired. Click Connect Instagram and log in again.",
                "username": connected_user,
            }

        cookies = await context.cookies("https://www.instagram.com")
        if not any(c.get("name") == "sessionid" for c in cookies):
            sessions.clear_session()
            return {
                "success": False,
                "message": "Session cookies missing. Connect Instagram again.",
                "username": connected_user,
            }

        label = connected_user or "your account"
        return {
            "success": True,
            "message": f"Connection successful — Instagram session active for @{label}.",
            "username": connected_user,
        }
    except Exception as exc:
        logger.warning("Instagram session validation failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "message": f"Could not verify Instagram session: {_format_error(exc)}",
            "username": connected_user,
        }
    finally:
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception:
            pass
