"""Facebook crawler — Graph API (token) or Playwright (login) or demo."""

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.facebook.graph_api import fetch_profile_comments
from crawlers.facebook.parser import parse_comments_from_html
from crawlers.facebook.session_manager import FacebookSessionManager
from crawlers.instagram.comment_monitor import CommentMonitor
from crawlers.instagram.screenshot import capture_page_screenshot
from services import system_settings as app_settings


class FacebookCrawler(BaseCrawler):
    DEMO_PHRASES = [
        "Tere posts pe roz comment karunga",
        "Fake news spread karti ho",
        "Group mein teri photo share kar di",
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(
            platform=Platform.FACEBOOK,
            storage_path=settings.SCREENSHOTS_PATH / "facebook",
            headless=settings.CRAWLER_HEADLESS,
            timeout_ms=settings.CRAWLER_TIMEOUT_MS,
            **kwargs,
        )
        self._sessions = FacebookSessionManager()
        self._page = None

    @property
    def demo_mode(self) -> bool:
        if app_settings.get_crawler_demo_mode():
            return True
        if settings.FACEBOOK_ACCESS_TOKEN:
            return False
        return not self._sessions.credentials_configured()

    @property
    def _use_graph_api(self) -> bool:
        return bool(settings.FACEBOOK_ACCESS_TOKEN) and not app_settings.get_crawler_demo_mode()

    async def setup_session(self) -> bool:
        if self.demo_mode or self._use_graph_api:
            self._is_running = True
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
        if self.demo_mode or self._use_graph_api:
            self._is_running = False
            return
        await super().teardown_session()

    async def _login_if_needed(self) -> bool:
        if self.demo_mode or self._use_graph_api or not self._page:
            return True
        if self._sessions.has_saved_session():
            return True
        email = app_settings.get_facebook_email()
        password = app_settings.get_facebook_password()
        if not email or not password:
            return False

        await self._page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await self._page.fill('input[name="email"]', email)
        await self._page.fill('input[name="pass"]', password)
        await self._page.click('button[name="login"]')
        await asyncio.sleep(6)
        await self._sessions.save_storage_state(self._context)
        return "login" not in (self._page.url or "")

    async def crawl_comments(
        self, target_username: str, post_url: str, max_comments: int = 100
    ) -> List[CrawledComment]:
        profile_url = post_url or f"https://www.facebook.com/{target_username}"

        if self.demo_mode:
            return self._demo_comments(target_username, profile_url, max_comments)

        if self._use_graph_api:
            token = settings.FACEBOOK_ACCESS_TOKEN
            assert token
            return await fetch_profile_comments(
                target_username, token, max_comments=max_comments
            )

        if not self._page:
            raise RuntimeError("Facebook browser session not initialized")

        await self._login_if_needed()
        await self.with_retry(
            self._page.goto,
            profile_url,
            wait_until="domcontentloaded",
            timeout=self.timeout_ms,
        )
        await self.rate_limit_wait(3.0)
        # Scroll to load comment sections on recent posts
        for _ in range(2):
            await self._page.mouse.wheel(0, 1200)
            await asyncio.sleep(1.5)

        html = await self._page.content()
        parsed = parse_comments_from_html(
            html,
            target_username=target_username,
            post_url=profile_url,
            max_comments=max_comments,
        )
        if not parsed:
            self.logger.warning(
                "No comments parsed from Facebook for %s — may need Page token or login",
                target_username,
            )
        return parsed

    def _demo_comments(
        self, target_username: str, post_url: str, max_comments: int
    ) -> List[CrawledComment]:
        count = min(max_comments, random.randint(2, 4))
        out: List[CrawledComment] = []
        for _ in range(count):
            accused = f"fb_user_{random.randint(100, 999)}"
            out.append(
                CrawledComment(
                    platform=self.platform.value,
                    text=random.choice(self.DEMO_PHRASES),
                    accused_username=accused,
                    accused_profile_url=f"https://facebook.com/{accused}",
                    target_username=target_username,
                    post_url=post_url,
                    comment_id=f"fb_{uuid4().hex[:8]}",
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
        profile_url = f"https://www.facebook.com/{target_username}"
        try:
            comments = await self.crawl_comments(target_username, profile_url, max_comments)
            new_comments = CommentMonitor(known_hashes).filter_new(comments)
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=True,
                comments=new_comments,
                pages_crawled=1,
                duration_seconds=duration,
            )
        except Exception as exc:
            self.logger.error("Facebook crawl failed for %s: %s", target_username, exc)
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=False,
                error=str(exc),
                duration_seconds=(datetime.now(timezone.utc) - started).total_seconds(),
            )
