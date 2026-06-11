"""
Instagram crawler — public profile + optional authenticated session.

When CRAWLER_DEMO_MODE=true (default without credentials), returns realistic
synthetic comments so the AI/evidence pipeline can be tested end-to-end.
"""

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, List, Optional
from uuid import uuid4

from configs.settings import settings
from services import system_settings as app_settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, CrawlerSessionError, Platform
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

    def __init__(
        self,
        *,
        login_username: Optional[str] = None,
        login_password: Optional[str] = None,
        headless: Optional[bool] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            platform=Platform.INSTAGRAM,
            storage_path=settings.SCREENSHOTS_PATH / "instagram",
            headless=headless if headless is not None else settings.CRAWLER_HEADLESS,
            timeout_ms=settings.CRAWLER_TIMEOUT_MS,
            **kwargs,
        )
        self._sessions = InstagramSessionManager()
        self._page = None
        self._login_username = login_username
        self._login_password = login_password
        self._last_login_error: Optional[str] = None

    @property
    def demo_mode(self) -> bool:
        return False

    def _credentials_missing_message(self) -> str:
        return (
            "Instagram not connected. In Settings, click Connect Instagram and log in "
            "in the browser window (session cookies are saved for crawls)."
        )

    def _has_instagram_auth(self) -> bool:
        if self._sessions.has_saved_session():
            return True
        if self._login_username and self._login_password:
            return True
        return app_settings.instagram_auth_configured()

    async def setup_session(self) -> bool:
        if not self._has_instagram_auth():
            self.logger.error(self._credentials_missing_message())
            return False
        try:
            ok = await self._launch_instagram_browser()
            if not ok or self._context is None or self._browser is None:
                self.logger.error("Playwright failed to launch browser for Instagram")
                return False

            storage = self._sessions.load_storage_state()
            if storage:
                try:
                    await self._context.close()
                    self._context = await self._browser.new_context(
                        storage_state=storage,
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1280, "height": 900},
                        locale="en-IN",
                    )
                    await self._context.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
                    )
                except Exception as exc:
                    self.logger.warning(
                        "Could not restore Instagram session file (%s); using fresh login",
                        exc,
                    )
                    self._context = await self._browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/122.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1280, "height": 900},
                        locale="en-IN",
                    )
                    await self._context.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
                    )

            self._page = await self._context.new_page()
            self._is_running = True
            return True
        except Exception as exc:
            self.logger.error("Instagram browser setup error: %s", exc, exc_info=True)
            return False

    async def _launch_instagram_browser(self) -> bool:
        """Launch Chromium; prefer installed Chrome/Edge on Windows (better for Instagram)."""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            launch_args = {
                "headless": self.headless,
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
                        browser = await self._playwright.chromium.launch(
                            channel=channel, **launch_args
                        )
                        self.logger.info("Using %s for Instagram", channel)
                    else:
                        browser = await self._playwright.chromium.launch(**launch_args)
                    break
                except Exception as exc:
                    self.logger.debug("Browser channel %s failed: %s", channel, exc)
            if not browser:
                return False
            self._browser = browser
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="en-IN",
            )
            await self._context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            self._is_running = True
            return True
        except Exception as exc:
            self.logger.error("Failed to initialize browser: %s", exc)
            return False

    async def teardown_session(self):
        self._page = None
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if hasattr(self, "_playwright") and self._playwright:
                await self._playwright.stop()
        except Exception as exc:
            self.logger.warning("Error during session teardown: %s", exc)
        self._is_running = False

    async def _dismiss_cookie_banner(self) -> None:
        if not self._page:
            return
        for label in (
            "Allow all cookies",
            "Allow essential and optional cookies",
            "Accept",
            "Accept All",
        ):
            try:
                btn = self._page.get_by_role("button", name=label, exact=False).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue

    def _resolve_login_credentials(self) -> tuple[Optional[str], Optional[str]]:
        user = (self._login_username or app_settings.get_instagram_username() or "").strip()
        pwd = self._login_password or app_settings.get_instagram_password() or ""
        return user or None, pwd or None

    async def _login_if_needed(self) -> bool:
        if not self._page:
            return False

        await self._page.goto("https://www.instagram.com/", wait_until="load", timeout=90000)
        await asyncio.sleep(2)
        await self._dismiss_cookie_banner()

        if "accounts/login" not in self._page.url.lower():
            self.logger.info("Instagram session active")
            return True

        user, pwd = self._resolve_login_credentials()
        if user and pwd:
            from crawlers.instagram.login_flow import perform_instagram_login

            ok, msg = await perform_instagram_login(self._page, user, pwd)
            if ok:
                await self._sessions.save_storage_state(self._context)
                self.logger.info("Instagram login: %s", msg)
                return True
            self.logger.warning("Instagram login failed: %s", msg)
            self._last_login_error = msg
            return False

        self._last_login_error = (
            "Instagram session expired. In Settings, click Connect Instagram and log in again."
        )
        self.logger.warning(self._last_login_error)
        return False

    async def crawl_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int = 100,
    ) -> List[CrawledComment]:
        if not app_settings.instagram_auth_configured():
            raise RuntimeError(self._credentials_missing_message())

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
        comment_text: Optional[str] = None,
    ) -> Optional[Path]:
        if self.demo_mode or not self._page:
            return None

        await self._page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        path = output_path or self.get_screenshot_path(f"shot_{uuid4().hex[:8]}")

        # Try to scroll to and capture the specific comment element
        if element_selector or comment_text:
            from crawlers.instagram.screenshot import capture_element_screenshot

            # First try explicit CSS selector if provided
            if element_selector:
                try:
                    el = self._page.locator(element_selector).first
                    if await el.count() > 0:
                        await el.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        result = await capture_element_screenshot(self._page, element_selector, path)
                        if result:
                            return result
                except Exception as exc:
                    self.logger.debug("Element selector screenshot failed: %s", exc)

            # Fall back: find comment by its text content and scroll to it
            if comment_text:
                snippet = comment_text[:60].strip()
                try:
                    # Expand comments if collapsed (click "View all X comments")
                    for load_label in ("View all", "Load more comments", "more comment"):
                        try:
                            btn = self._page.get_by_text(load_label, exact=False).first
                            if await btn.is_visible(timeout=2000):
                                await btn.click()
                                await asyncio.sleep(1.5)
                                break
                        except Exception:
                            pass

                    # Locate the comment span/div containing our snippet
                    comment_el = self._page.get_by_text(snippet, exact=False).first
                    if await comment_el.count() > 0:
                        await comment_el.scroll_into_view_if_needed()
                        await asyncio.sleep(0.8)
                        # Grab the closest comment container (article or li ancestor)
                        container = self._page.locator(
                            "li:has-text('" + snippet.replace("'", "\\'") + "'), "
                            "div[role='dialog']:has-text('" + snippet.replace("'", "\\'") + "')"
                        ).first
                        if await container.count() > 0:
                            await container.screenshot(path=str(path))
                            return path
                        # If no container found, take a viewport screenshot centred on the element
                        await capture_page_screenshot(self._page, path)
                        return path
                except Exception as exc:
                    self.logger.debug("Comment-text scroll screenshot failed: %s", exc)

        # Default: full-page screenshot
        return await capture_page_screenshot(self._page, path)

    async def crawl_target_profile(
        self,
        target_username: str,
        *,
        max_comments: int = 50,
        known_hashes: Optional[set[str]] = None,
        historical: bool = False,
        max_posts: Optional[int] = None,
        max_comments_per_post: Optional[int] = None,
        checkpoint: Optional[object] = None,
        on_post_saved: Optional[Callable[[], Awaitable[None]]] = None,
        crawl_target_id: Optional[str] = None,
    ) -> CrawlResult:
        """
        Full crawl for a target profile.

        Regular: quick pass on profile page (recent visible comments).
        Historical: scroll profile for older posts, open each post, crawl all comments.
        """
        started = datetime.now(timezone.utc)
        post_url = f"https://www.instagram.com/{target_username}/"
        crawl_progress: dict = {}

        try:
            if not self._page:
                raise CrawlerSessionError(
                    "Browser session not initialized. "
                    + self._credentials_missing_message()
                    if not app_settings.instagram_auth_configured()
                    else (
                        "Restart the API (without --reload on Windows), ensure "
                        "`python -m playwright install chromium` was run, and test "
                        "Instagram connection in Settings."
                    )
                )

            if historical:
                comments, pages, crawl_progress = await self._crawl_historical(
                    target_username,
                    max_posts=max_posts or settings.HISTORICAL_CRAWL_MAX_POSTS,
                    max_comments_per_post=max_comments_per_post
                    or settings.HISTORICAL_CRAWL_MAX_COMMENTS_PER_POST,
                    checkpoint=checkpoint,
                    on_post_saved=on_post_saved,
                    crawl_target_id=crawl_target_id,
                )
            else:
                comments = await self.crawl_comments(target_username, post_url, max_comments)
                pages = 1

            monitor = CommentMonitor(known_hashes)
            new_comments = monitor.filter_new(comments)
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            progress = crawl_progress if historical else {}
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=True,
                comments=new_comments,
                pages_crawled=pages,
                duration_seconds=duration,
                crawl_progress=progress,
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

    async def _crawl_historical(
        self,
        target_username: str,
        *,
        max_posts: int,
        max_comments_per_post: int,
        checkpoint: Optional[object] = None,
        on_post_saved: Optional[Callable[[], Awaitable[None]]] = None,
        crawl_target_id: Optional[str] = None,
    ) -> tuple[List[CrawledComment], int, dict]:
        """Scroll profile, visit posts, incremental comments using per-target checkpoint."""
        from crawlers.instagram.historical import collect_post_urls, crawl_post_comments
        from services.crawl_checkpoint import build_run_progress_entry, extract_post_id

        if not self._page:
            raise RuntimeError("Browser session not initialized")

        logged_in = await self._login_if_needed()
        if not logged_in:
            self.logger.warning(
                "Instagram login not confirmed for @%s — attempting public profile crawl",
                target_username,
            )
        self.logger.info(
            "Historical crawl @%s: up to %d posts, %d comments/post (checkpoint=%s)",
            target_username,
            max_posts,
            max_comments_per_post,
            "yes" if checkpoint else "no",
        )

        post_urls = await collect_post_urls(
            self._page,
            target_username,
            max_posts=max_posts,
            scroll_rounds=settings.HISTORICAL_CRAWL_PROFILE_SCROLLS,
            crawl_target_id=crawl_target_id,
        )

        from websocket.events import broadcast_crawl_activity

        await broadcast_crawl_activity(
            target_username=target_username,
            activity_type="collecting_posts",
            message=f"Found {len(post_urls)} posts on @{target_username}'s profile",
            platform="instagram",
        )

        ckpt = checkpoint
        if ckpt and ckpt.pending_post_urls:
            merged = list(dict.fromkeys(ckpt.pending_post_urls + post_urls))
            post_urls = merged[:max_posts]
        if ckpt:
            ckpt.pending_post_urls = list(post_urls)

        if not post_urls:
            self.logger.warning("No post URLs found for @%s — falling back to profile page", target_username)
            comments = await self.crawl_comments(
                target_username,
                f"https://www.instagram.com/{target_username}/",
                max_comments_per_post * max(1, max_posts // 2),
            )
            return comments, 1, {"posts": [], "fallback": "profile_page"}

        all_comments: List[CrawledComment] = []
        run_posts: list[dict] = []
        from services.crawl_pause import check_crawl_pause

        for i, url in enumerate(post_urls, start=1):
            await check_crawl_pause(crawl_target_id)
            pid = extract_post_id(url)
            post_cp = ckpt.get_post(url) if ckpt else None
            known_ids = post_cp.known_comment_ids if post_cp else set()
            known_hashes = post_cp.known_hashes if post_cp else set()

            self.logger.info(
                "Historical post %d/%d: %s (known_ids=%d, incremental=%s)",
                i,
                len(post_urls),
                url,
                len(known_ids),
                bool(known_ids or known_hashes),
            )
            try:
                await broadcast_crawl_activity(
                    target_username=target_username,
                    activity_type="opening_post",
                    message=f"Opening post {i}/{len(post_urls)}",
                    detail=url,
                    platform="instagram",
                )
                outcome = await crawl_post_comments(
                    self._page,
                    url,
                    target_username,
                    max_comments_per_post,
                    self.rate_limit_wait,
                    known_comment_ids=known_ids,
                    known_hashes=known_hashes,
                    incremental=True,
                    crawl_target_id=crawl_target_id,
                )
                batch = outcome.comments
                all_comments.extend(batch)

                if ckpt:
                    ckpt.register_comments(url, batch)
                    # Only mark post fully crawled when we found overlap with
                    # known comments AND no new comments were discovered. This
                    # means we've exhausted the comment thread for this post.
                    # If new comments were found, the post may still receive more.
                    no_new_found = len(batch) == 0
                    if outcome.stopped_at_known and no_new_found:
                        ckpt.mark_post_complete(url, fully=True)
                    elif len(batch) > 0:
                        # New comments found — post is actively receiving comments,
                        # so reset fully_crawled to ensure we re-check next run.
                        ckpt.mark_post_complete(url, fully=False)
                    if url in ckpt.pending_post_urls:
                        ckpt.pending_post_urls = [u for u in ckpt.pending_post_urls if u != url]
                    if on_post_saved:
                        await on_post_saved()

                run_posts.append(
                    build_run_progress_entry(
                        url,
                        new_comments=len(batch),
                        stopped_at_known=outcome.stopped_at_known,
                    )
                )
                await broadcast_crawl_activity(
                    target_username=target_username,
                    activity_type="post_complete",
                    message=f"Post {i}/{len(post_urls)}: found {len(batch)} new comment{'s' if len(batch) != 1 else ''}",
                    detail=url,
                    platform="instagram",
                )
            except Exception as exc:
                self.logger.warning("Failed post %s: %s", url, exc)
                run_posts.append(
                    {
                        "post_id": pid,
                        "post_url": url,
                        "error": str(exc),
                        "new_comments": 0,
                    }
                )
            await self.rate_limit_wait(settings.HISTORICAL_CRAWL_POST_DELAY_SEC)

        progress = {
            "profile_username": target_username,
            "posts_total": len(post_urls),
            "posts": run_posts,
            "comments_collected": len(all_comments),
        }
        if ckpt:
            progress["checkpoint"] = {
                "posts_tracked": len(ckpt.posts),
                "posts_completed": sum(1 for p in ckpt.posts.values() if p.fully_crawled),
                "pending_posts": len(ckpt.pending_post_urls),
            }

        self.logger.info(
            "Historical crawl @%s: %d posts, %d new comments this run",
            target_username,
            len(post_urls),
            len(all_comments),
        )
        return all_comments, len(post_urls), progress
