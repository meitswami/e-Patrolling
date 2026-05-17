"""
Instagram crawler — public profile + optional authenticated session.

When CRAWLER_DEMO_MODE=true (default without credentials), returns realistic
synthetic comments so the AI/evidence pipeline can be tested end-to-end.
"""

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from services import system_settings as app_settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.instagram.comment_monitor import CommentMonitor
from crawlers.instagram.parser import parse_comments_from_html
from crawlers.instagram.screenshot import capture_page_screenshot
from crawlers.instagram.session_manager import InstagramSessionManager


class InstagramCrawler(BaseCrawler):
    """Instagram platform crawler."""

    DEMO_PHRASES = [
        "Tu bahar aa kabhi, sabak sikhaunga",
        "Fake influencer, paid PR",
        "Aise kapde pehen ke attention maangti hai",
        "Block kar diya phir bhi dekh lunga",
        "Nice photo 🙂",
        "Report kar dunga police mein",
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(
            platform=Platform.INSTAGRAM,
            storage_path=settings.SCREENSHOTS_PATH / "instagram",
            headless=settings.CRAWLER_HEADLESS,
            timeout_ms=settings.CRAWLER_TIMEOUT_MS,
            **kwargs,
        )
        self._sessions = InstagramSessionManager()
        self._page = None

    @property
    def demo_mode(self) -> bool:
        if app_settings.get_crawler_demo_mode():
            return True
        return not app_settings.instagram_credentials_configured()

    async def setup_session(self) -> bool:
        if self.demo_mode:
            self._is_running = True
            self.logger.info("Instagram crawler in demo mode — skipping browser")
            return True
        ok = await super().setup_session()
        if not ok or self._context is None:
            return False

        storage = self._sessions.load_storage_state()
        if storage:
            await self._context.close()
            self._context = await self._browser.new_context(
                storage_state=storage,
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="en-IN",
            )

        self._page = await self._context.new_page()
        return True

    async def teardown_session(self):
        if self.demo_mode:
            self._is_running = False
            return
        await super().teardown_session()

    async def _login_if_needed(self) -> bool:
        if self.demo_mode or not self._sessions.credentials_configured():
            return True
        if self._sessions.has_saved_session():
            return True
        if not self._page:
            return False

        user = app_settings.get_instagram_username()
        password = app_settings.get_instagram_password()
        assert user and password

        await self._page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await self._page.fill('input[name="username"]', user)
        await self._page.fill('input[name="password"]', password)
        await self._page.click('button[type="submit"]')
        await asyncio.sleep(5)
        await self._sessions.save_storage_state(self._context)
        return "login" not in self._page.url

    async def crawl_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int = 100,
    ) -> List[CrawledComment]:
        if self.demo_mode:
            return self._demo_comments(target_username, post_url, max_comments)

        if not self._page:
            raise RuntimeError("Browser session not initialized")

        await self._login_if_needed()
        profile_url = post_url or f"https://www.instagram.com/{target_username}/"
        await self.with_retry(self._page.goto, profile_url, wait_until="domcontentloaded")
        await self.rate_limit_wait(3.0)
        html = await self._page.content()
        parsed = parse_comments_from_html(
            html,
            platform=self.platform.value,
            target_username=target_username,
            post_url=profile_url,
            max_comments=max_comments,
        )
        if parsed:
            return parsed

        self.logger.warning(
            "No comments parsed from Instagram for @%s — page may require login",
            target_username,
        )
        return []

    def _demo_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int,
    ) -> List[CrawledComment]:
        """Synthetic comments for pipeline testing without Instagram access."""
        count = min(max_comments, random.randint(2, 5))
        comments: List[CrawledComment] = []
        for i in range(count):
            text = random.choice(self.DEMO_PHRASES)
            accused = f"demo_troll_{random.randint(10, 99)}"
            post_id = f"demo_post_{uuid4().hex[:8]}"
            comment_id = f"demo_cmt_{uuid4().hex[:8]}"
            from osint.demo_enrichment import demo_profile_enrichment
            from osint.permaliinks import build_comment_permalink

            enrich = demo_profile_enrichment(accused, "instagram")
            purl = post_url or f"https://www.instagram.com/{target_username}/"
            comments.append(
                CrawledComment(
                    platform=self.platform.value,
                    text=text,
                    accused_username=accused,
                    accused_display_name=f"Demo User {i + 1}",
                    accused_profile_url=f"https://www.instagram.com/{accused}/",
                    accused_avatar_url=enrich["accused_avatar_url"],
                    target_username=target_username,
                    post_url=purl,
                    post_id=post_id,
                    comment_id=comment_id,
                    comment_url=build_comment_permalink(
                        "instagram",
                        username=accused,
                        post_id=post_id,
                        comment_id=comment_id,
                        post_url=purl,
                    ),
                    timestamp=datetime.now(timezone.utc),
                    raw_data=enrich,
                )
            )
        self.logger.info("Demo mode: generated %d synthetic comments for @%s", count, target_username)
        return comments

    async def take_screenshot(
        self,
        url: str,
        element_selector: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        if self.demo_mode or not self._page:
            return None

        await self._page.goto(url, wait_until="domcontentloaded")
        path = output_path or self.get_screenshot_path(f"shot_{uuid4().hex[:8]}")
        return await capture_page_screenshot(self._page, path)

    async def crawl_target_profile(
        self,
        target_username: str,
        *,
        max_comments: int = 50,
        known_hashes: Optional[set[str]] = None,
    ) -> CrawlResult:
        """Full crawl cycle for a target's profile (recent post context)."""
        started = datetime.now(timezone.utc)
        post_url = f"https://www.instagram.com/{target_username}/"

        try:
            comments = await self.crawl_comments(target_username, post_url, max_comments)
            monitor = CommentMonitor(known_hashes)
            new_comments = monitor.filter_new(comments)
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
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            self.logger.error("Crawl failed for @%s: %s", target_username, exc)
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=False,
                error=str(exc),
                duration_seconds=duration,
            )
