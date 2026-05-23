"""
PATROL — Base Crawler
=====================
Abstract base class that ALL platform crawlers must inherit.

Enforces consistent interface:
  - Session management
  - Rate limiting
  - Screenshot capture
  - Queue integration
  - Error handling + retry logic

Usage:
    class InstagramCrawler(BaseCrawler):
        async def crawl_comments(self, url: str) -> List[CrawledComment]:
            ...
"""

import asyncio
import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class CrawlerSessionError(RuntimeError):
    """Browser/credentials setup failed before crawling."""


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


@dataclass
class CrawledComment:
    """
    Standardized comment data extracted from any platform.
    This is the contract between crawlers and the AI pipeline.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    platform: str = ""
    
    # Content
    text: str = ""
    language_hint: Optional[str] = None  # Pre-detected if available
    
    # Accused (commenter)
    accused_username: str = ""
    accused_display_name: str = ""
    accused_profile_url: str = ""
    accused_avatar_url: str = ""
    accused_follower_count: Optional[int] = None
    accused_is_verified: bool = False
    
    # Target (who received the comment)
    target_username: str = ""
    target_platform_id: str = ""
    
    # Location context
    post_url: str = ""
    comment_url: Optional[str] = None
    post_id: str = ""
    comment_id: str = ""
    
    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    
    # Raw data (platform-specific)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def content_hash(self) -> str:
        """Unique hash of comment content for deduplication."""
        content = f"{self.platform}:{self.comment_id}:{self.text}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class CrawlResult:
    """Result from a crawl session."""
    platform: Platform
    target_username: str
    success: bool
    comments: List[CrawledComment] = field(default_factory=list)
    error: Optional[str] = None
    pages_crawled: int = 0
    duration_seconds: float = 0.0
    crawled_at: datetime = field(default_factory=datetime.utcnow)
    crawl_progress: Dict[str, Any] = field(default_factory=dict)


class BaseCrawler(ABC):
    """
    Abstract base crawler. All platform crawlers inherit this.
    
    Subclasses MUST implement:
      - crawl_comments()
      - take_screenshot()
    
    Subclasses SHOULD override:
      - setup_session()
      - teardown_session()
    """

    def __init__(
        self,
        platform: Platform,
        storage_path: Optional[Path] = None,
        headless: bool = True,
        timeout_ms: int = 30000,
        max_retries: int = 3,
    ):
        self.platform = platform
        self.storage_path = storage_path or Path(f"./storage/screenshots/{platform.value}")
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self.logger = get_logger(f"crawler.{platform.value}")
        
        self._browser = None
        self._context = None
        self._is_running = False
        self._rate_limit_delay = 2.0  # Seconds between requests

    # ── Abstract methods (must implement) ──────────────────

    @abstractmethod
    async def crawl_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int = 100,
    ) -> List[CrawledComment]:
        """
        Crawl comments from a specific post.
        Must return standardized CrawledComment objects.
        """
        ...

    @abstractmethod
    async def take_screenshot(
        self,
        url: str,
        element_selector: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Capture screenshot of URL or specific element.
        Returns path to saved screenshot, or None on failure.
        """
        ...

    # ── Lifecycle (override as needed) ─────────────────────

    async def setup_session(self) -> bool:
        """
        Initialize browser session.
        Override in subclasses for authenticated crawling.
        Returns True if session is ready.
        """
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
                locale="en-IN",
            )
            self._is_running = True
            self.logger.info(f"Browser session initialized for {self.platform.value}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            return False

    async def teardown_session(self):
        """Close browser and cleanup resources."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if hasattr(self, "_playwright"):
                await self._playwright.stop()
            self._is_running = False
            self.logger.info(f"Browser session closed for {self.platform.value}")
        except Exception as e:
            self.logger.warning(f"Error during session teardown: {e}")

    # ── Retry logic ────────────────────────────────────────

    async def with_retry(self, func, *args, **kwargs) -> Any:
        """
        Execute async function with exponential backoff retry.
        Retries up to self.max_retries times.
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait_seconds = (2 ** attempt) * 1.5
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {wait_seconds}s..."
                )
                await asyncio.sleep(wait_seconds)

        self.logger.error(f"All {self.max_retries} attempts failed. Last error: {last_error}")
        raise last_error

    # ── Rate limiting ──────────────────────────────────────

    async def rate_limit_wait(self, custom_delay: Optional[float] = None):
        """Wait to respect platform rate limits."""
        delay = custom_delay or self._rate_limit_delay
        await asyncio.sleep(delay)

    # ── Screenshot helpers ─────────────────────────────────

    def get_screenshot_path(self, evidence_id: str) -> Path:
        """Generate storage path: storage/screenshots/platform/YYYY/MM/DD/id.png"""
        now = datetime.utcnow()
        path = self.storage_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}"
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{evidence_id}.png"

    # ── Context manager support ────────────────────────────

    async def __aenter__(self):
        ok = await self.setup_session()
        if not ok:
            raise CrawlerSessionError(
                f"{self.platform.value} browser session failed to start. "
                "Connect Instagram in Settings (browser login), run "
                "`python -m playwright install chromium` in backend/.venv, and "
                "restart the API without --reload if crawls fail on Windows."
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.teardown_session()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(platform={self.platform.value}, running={self._is_running})>"