"""Telegram crawler — demo mode MVP (Telethon for production)."""

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.instagram.comment_monitor import CommentMonitor


class TelegramCrawler(BaseCrawler):
    DEMO_PHRASES = [
        "Channel pe teri photo viral kar dunga",
        "Admin ko tag karke ban karwa dunga",
        "Roz message karunga",
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(
            platform=Platform.TELEGRAM,
            storage_path=settings.SCREENSHOTS_PATH / "telegram",
            **kwargs,
        )

    @property
    def demo_mode(self) -> bool:
        return settings.CRAWLER_DEMO_MODE or not (
            settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH
        )

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
            accused = f"tg_user_{random.randint(100, 999)}"
            out.append(
                CrawledComment(
                    platform=self.platform.value,
                    text=random.choice(self.DEMO_PHRASES),
                    accused_username=accused,
                    accused_profile_url=f"https://t.me/{accused}",
                    target_username=target_username,
                    post_url=post_url or f"https://t.me/{target_username}",
                    comment_id=f"tg_{uuid4().hex[:8]}",
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
                target_username, f"https://t.me/{target_username}", max_comments
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
