"""Robust Instagram login for Playwright (handles cookie banners and UI changes)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

USERNAME_SELECTORS = (
    'input[name="username"]',
    "#loginForm input[name='username']",
    'input[aria-label="Phone number, username, or email"]',
    'input[aria-label="Mobile number, username or email"]',
    'input[aria-label*="username" i]',
    'input[aria-label*="email" i]',
    'input[autocomplete="username"]',
)

PASSWORD_SELECTORS = (
    'input[name="password"]',
    "#loginForm input[name='password']",
    'input[aria-label="Password"]',
    'input[type="password"]',
)


async def dismiss_cookie_banner(page) -> None:
    for label in (
        "Allow all cookies",
        "Allow essential and optional cookies",
        "Decline optional cookies",
        "Only allow essential cookies",
        "Accept",
        "Accept All",
        "OK",
    ):
        try:
            btn = page.get_by_role("button", name=label, exact=False).first
            if await btn.is_visible(timeout=1200):
                await btn.click()
                await asyncio.sleep(1)
                return
        except Exception:
            continue


async def _find_visible_locator(page, selectors: tuple[str, ...], timeout_ms: int = 90000):
    combined = ", ".join(selectors)
    loc = page.locator(combined).first
    try:
        await loc.wait_for(state="visible", timeout=timeout_ms)
        return loc
    except Exception as exc:
        raise TimeoutError(
            "Instagram login form did not appear. Instagram may be blocking the automated "
            "browser, or the page layout changed."
        ) from exc


async def _open_login_page(page) -> None:
    urls = (
        "https://www.instagram.com/accounts/login/",
        "https://www.instagram.com/accounts/login/?next=%2F",
    )
    last_err: Optional[Exception] = None
    for url in urls:
        try:
            await page.goto(url, wait_until="load", timeout=90000)
            await asyncio.sleep(3)
            await dismiss_cookie_banner(page)
            if "instagram.com" in page.url.lower():
                return
        except Exception as exc:
            last_err = exc
            logger.warning("Login page load failed for %s: %s", url, exc)
    if last_err:
        raise last_err


async def _go_to_login_from_home(page) -> None:
    """If already on home, click Log in link."""
    try:
        link = page.get_by_role("link", name=re.compile(r"^log\s*in$", re.I)).first
        if await link.is_visible(timeout=3000):
            await link.click()
            await asyncio.sleep(2)
    except Exception:
        pass


async def save_login_debug_screenshot(page) -> Optional[str]:
    try:
        out = settings.LOGS_PATH / "instagram_login_debug.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out), full_page=True)
        return str(out)
    except Exception as exc:
        logger.warning("Could not save login debug screenshot: %s", exc)
        return None


async def perform_instagram_login(page, username: str, password: str) -> tuple[bool, str]:
    """
    Try to log in. Returns (success, message).
    """
    user = username.strip()
    pwd = password
    if not user or not pwd:
        return False, "Username and password are required."

    try:
        await page.goto("https://www.instagram.com/", wait_until="load", timeout=90000)
        await asyncio.sleep(2)
        await dismiss_cookie_banner(page)

        if "accounts/login" not in page.url.lower():
            body = (await page.inner_text("body"))[:1500].lower()
            if "log in" in body and "sign up" in body:
                await _go_to_login_from_home(page)

        if "accounts/login" not in page.url.lower() and "login" not in page.url.lower():
            logger.info("Already logged in or no login redirect")
            return True, "Session already active"

        await _open_login_page(page)
        await _go_to_login_from_home(page)

        user_input = await _find_visible_locator(page, USERNAME_SELECTORS, timeout_ms=90000)
        pass_input = await _find_visible_locator(page, PASSWORD_SELECTORS, timeout_ms=30000)

        await user_input.click()
        await user_input.fill(user)
        await asyncio.sleep(0.5)
        await pass_input.click()
        await pass_input.fill(pwd)
        await asyncio.sleep(0.5)

        submit = page.locator(
            'button[type="submit"], div[role="button"]:has-text("Log in"), '
            'button:has-text("Log in")'
        ).first
        await submit.click()
        await asyncio.sleep(10)

        url = page.url.lower()
        body = (await page.inner_text("body"))[:3000].lower()

        if "challenge" in url or "two_factor" in url or "two-factor" in body:
            return False, (
                "Instagram wants 2FA or a security check. Log in once in normal Chrome "
                "at instagram.com, then test again."
            )
        if "incorrect" in body or ("sorry" in body and "password" in body):
            return False, "Instagram rejected the username or password."
        if "accounts/login" in url or ("/login" in url and "instagram" in url):
            shot = await save_login_debug_screenshot(page)
            extra = f" Debug screenshot: {shot}" if shot else ""
            return False, (
                "Still on the login page after submit. Check credentials, or set "
                "CRAWLER_HEADLESS=false in .env and retry (visible browser)."+ extra
            )

        return True, f"Logged in as @{user}"

    except TimeoutError as exc:
        shot = await save_login_debug_screenshot(page)
        extra = f" Screenshot saved: {shot}" if shot else ""
        return False, (
            f"{exc} Try: (1) CRAWLER_HEADLESS=false in .env, (2) log in at instagram.com "
            f"in Chrome first, (3) check network/VPN.{extra}"
        )
    except Exception as exc:
        shot = await save_login_debug_screenshot(page)
        extra = f" Screenshot: {shot}" if shot else ""
        return False, f"Login error: {exc}{extra}"
