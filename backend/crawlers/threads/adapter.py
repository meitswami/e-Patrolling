"""Threads crawler — demo mode MVP."""

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from services import system_settings as app_settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.instagram.comment_monitor import CommentMonitor


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
            **kwargs,
        )

    @property
    def demo_mode(self) -> bool:
        return app_settings.get_crawler_demo_mode()

    async def setup_session(self) -> bool:
        self._is_running = True
        return True

    async def teardown_session(self) -> None:
        self._is_running = False

    async def crawl_comments(
        self, target_username: str, post_url: str, max_comments: int = 100
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
                    post_url=post_url or f"https://www.threads.net/@{target_username}",
                    comment_id=f"th_{uuid4().hex[:8]}",
                    timestamp=datetime.now(timezone.utc),
                    raw_data={"source": "demo_mode"},
                )
            )
        return out

    async def take_screenshot(
        self, url: str, element_selector: Optional[str] = None, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        return output_path

    async def crawl_target_profile(
        self, target_username: str, *, max_comments: int = 50, known_hashes: Optional[set] = None
    ) -> CrawlResult:
        started = datetime.now(timezone.utc)
        try:
            comments = await self.crawl_comments(
                target_username, f"https://www.threads.net/@{target_username}", max_comments
            )
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
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=False,
                error=str(exc),
                duration_seconds=(datetime.now(timezone.utc) - started).total_seconds(),
            )
