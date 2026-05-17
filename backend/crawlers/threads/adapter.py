"""Threads crawler — Playwright (Instagram login) or demo."""

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.instagram.comment_monitor import CommentMonitor
from crawlers.instagram.screenshot import capture_page_screenshot
from crawlers.threads.parser import parse_comments_from_html
from crawlers.threads.session_manager import ThreadsSessionManager
from services import system_settings as app_settings


class ThreadsCrawler(BaseCrawler):
    DEMO_PHRASES = [
        "Teri thread pe roz aaunga",
        "Block kiya phir bhi dekh lunga",
        "Fake influencer",
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(
            platform=Platform.THREADS,
            storage_path=settings.SCREENSHOTS_PATH / "threads",
            headless=settings.CRAWLER_HEADLESS,
            timeout_ms=settings.CRAWLER_TIMEOUT_MS,
            **kwargs,
        )
        self._sessions = ThreadsSessionManager()
        self._page = None

    @property
    def demo_mode(self) -> bool:
        if app_settings.get_crawler_demo_mode():
            return True
        return not self._sessions.credentials_configured()

    async def setup_session(self) -> bool:
        if self.demo_mode:
            self._is_running = True
            self.logger.info("Threads crawler in demo mode")
            return True
        ok = await super().setup_session()
        if not ok or self._context is None:
            return False
        storage = self._sessions.load_storage_state()
        if storage:
            await self._context.close()
            self._context = await self._browser.new_context(
                storage_state=storage,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
        self._page = await self._context.new_page()
        return True

    async def teardown_session(self) -> None:
        if self.demo_mode:
            self._is_running = False
            return
        await super().teardown_session()

    async def _ensure_threads_access(self) -> bool:
        """Open threads.net; use Instagram SSO if redirected to login."""
        if not self._page:
            return False
        profile_check = "https://www.threads.net/"
        await self._page.goto(profile_check, wait_until="domcontentloaded", timeout=self.timeout_ms)
        await asyncio.sleep(2)
        if "login" not in (self._page.url or "").lower():
            return True

        # Try Instagram login button on Threads
        try:
            ig_btn = self._page.locator('text="Continue with Instagram"').first
            if await ig_btn.count() > 0:
                await ig_btn.click()
                await asyncio.sleep(5)
                return "login" not in (self._page.url or "").lower()
        except Exception:
            pass

        # Fallback: log in via Instagram then return to Threads
        user = app_settings.get_instagram_username()
        password = app_settings.get_instagram_password()
        if not user or not password:
            return False

        await self._page.goto(
            "https://www.instagram.com/accounts/login/",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(2)
        await self._page.fill('input[name="username"]', user)
        await self._page.fill('input[name="password"]', password)
        await self._page.click('button[type="submit"]')
        await asyncio.sleep(5)
        await self._page.goto("https://www.threads.net/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        return "login" not in (self._page.url or "").lower()

    async def crawl_comments(
        self, target_username: str, post_url: str, max_comments: int = 100
    ) -> List[CrawledComment]:
        handle = target_username.lstrip("@")
        profile_url = post_url or f"https://www.threads.net/@{handle}"

        if self.demo_mode:
            return self._demo_comments(handle, profile_url, max_comments)

        if not self._page:
            raise RuntimeError("Threads browser session not initialized")

        await self._ensure_threads_access()
        await self.with_retry(
            self._page.goto,
            profile_url,
            wait_until="domcontentloaded",
            timeout=self.timeout_ms,
        )
        await self.rate_limit_wait(3.0)
        for _ in range(2):
            await self._page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.2)

        html = await self._page.content()
        parsed = parse_comments_from_html(
            html,
            target_username=handle,
            post_url=profile_url,
            max_comments=max_comments,
        )
        if not parsed:
            self.logger.warning(
                "No threads parsed for @%s — check Instagram login in Settings",
                handle,
            )
        return parsed

    def _demo_comments(
        self, target_username: str, post_url: str, max_comments: int
    ) -> List[CrawledComment]:
        count = min(max_comments, random.randint(2, 3))
        out: List[CrawledComment] = []
        for _ in range(count):
            accused = f"threads_{random.randint(10, 99)}"
            out.append(
                CrawledComment(
                    platform=self.platform.value,
                    text=random.choice(self.DEMO_PHRASES),
                    accused_username=accused,
                    accused_profile_url=f"https://www.threads.net/@{accused}",
                    target_username=target_username,
                    post_url=post_url,
                    comment_id=f"th_{uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    raw_data={"source": "demo_mode"},
                )
            )
        return out

    async def take_screenshot(
        self, url: str, element_selector: Optional[str] = None, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        if self.demo_mode or not self._page:
            return None
        await self._page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        path = output_path or self.get_screenshot_path(f"shot_{uuid4().hex[:8]}")
        return await capture_page_screenshot(self._page, path)

    async def crawl_target_profile(
        self, target_username: str, *, max_comments: int = 50, known_hashes: Optional[set] = None
    ) -> CrawlResult:
        started = datetime.now(timezone.utc)
        handle = target_username.lstrip("@")
        try:
            comments = await self.crawl_comments(
                handle, f"https://www.threads.net/@{handle}", max_comments
            )
            new_comments = CommentMonitor(known_hashes).filter_new(comments)
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            return CrawlResult(
                platform=self.platform,
                target_username=handle,
                success=True,
                comments=new_comments,
                pages_crawled=1,
                duration_seconds=duration,
            )
        except Exception as exc:
            self.logger.error("Threads crawl failed for @%s: %s", handle, exc)
            return CrawlResult(
                platform=self.platform,
                target_username=handle,
                success=False,
                error=str(exc),
                duration_seconds=(datetime.now(timezone.utc) - started).total_seconds(),
            )
