"""Open a real browser for manual Instagram login; persist Playwright session cookies."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Optional

from crawlers.instagram.session_manager import InstagramSessionManager
from utils.logger import get_logger

logger = get_logger(__name__)

LOGIN_TIMEOUT_SEC = 300
LOGIN_URL_MARKERS = ("accounts/login", "/login?")


async def _launch_browser(headless: bool = False):
    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    launch_args = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    }
    browser = None
    for channel in ("chrome", "msedge", None):
        try:
            if channel:
                browser = await playwright.chromium.launch(channel=channel, **launch_args)
            else:
                browser = await playwright.chromium.launch(**launch_args)
            break
        except Exception as exc:
            logger.debug("Launch channel %s failed: %s", channel, exc)
    if not browser:
        await playwright.stop()
        raise RuntimeError(
            "Could not start a browser. Install Chrome or run: python -m playwright install chromium"
        )
    return playwright, browser


async def _has_session_cookie(context) -> bool:
    cookies = await context.cookies("https://www.instagram.com")
    return any(c.get("name") == "sessionid" and c.get("value") for c in cookies)


async def _detect_username(page) -> Optional[str]:
    try:
        html = await page.content()
        for pattern in (
            r'"username"\s*:\s*"([^"]+)"',
            r'"viewer"\s*:\s*\{[^}]*"username"\s*:\s*"([^"]+)"',
        ):
            match = re.search(pattern, html)
            if match:
                name = match.group(1).strip()
                if name and name not in ("instagram", "meta"):
                    return name
    except Exception as exc:
        logger.debug("Username detect failed: %s", exc)
    return None


async def _wait_for_manual_login(page, context) -> bool:
    """Poll until user finishes login in the opened browser window."""
    start = time.monotonic()
    while time.monotonic() - start < LOGIN_TIMEOUT_SEC:
        url = (page.url or "").lower()
        on_login = any(marker in url for marker in LOGIN_URL_MARKERS)
        if await _has_session_cookie(context) and not on_login:
            return True
        if "instagram.com" in url and not on_login:
            try:
                home = page.locator(
                    'svg[aria-label="Home"], a[href="/direct/inbox/"], '
                    'a[href*="/accounts/edit/"]'
                ).first
                if await home.is_visible(timeout=1500):
                    return True
            except Exception:
                pass
        await asyncio.sleep(2)
    return False


async def connect_instagram_via_browser() -> dict[str, Any]:
    """
    Open Instagram in a visible browser. User logs in manually; cookies are saved.
    Returns {success, message, username, session_saved}.
    """
    sessions = InstagramSessionManager()
    playwright = None
    browser = None
    context = None
    page = None

    try:
        playwright, browser = await _launch_browser(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-IN",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        page = await context.new_page()
        await page.goto("https://www.instagram.com/accounts/login/", wait_until="load", timeout=90000)

        logger.info("Instagram connect: waiting for manual login in browser window")
        logged_in = await _wait_for_manual_login(page, context)
        if not logged_in:
            return {
                "success": False,
                "message": (
                    "Login timed out after 5 minutes. Click Connect again, log in on Instagram "
                    "in the browser window, then wait until you see your feed."
                ),
                "username": None,
                "session_saved": False,
            }

        await page.goto("https://www.instagram.com/", wait_until="load", timeout=60000)
        await asyncio.sleep(2)
        username = await _detect_username(page)
        await sessions.save_storage_state(context)
        if username:
            sessions.save_meta(username=username)

        return {
            "success": True,
            "message": (
                f"Instagram connected"
                + (f" as @{username}" if username else "")
                + ". Session cookies saved — crawls will use this login."
            ),
            "username": username,
            "session_saved": True,
        }
    except Exception as exc:
        logger.warning("Instagram connect failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "message": f"Could not open Instagram login: {exc}",
            "username": None,
            "session_saved": False,
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
        except Exception as exc:
            logger.debug("Connect teardown: %s", exc)


async def disconnect_instagram_session() -> dict[str, Any]:
    sessions = InstagramSessionManager()
    sessions.clear_session()
    return {
        "success": True,
        "message": "Instagram session removed. Connect again to log in.",
        "username": None,
        "session_saved": False,
    }
