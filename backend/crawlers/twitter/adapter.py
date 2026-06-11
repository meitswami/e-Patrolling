"""Twitter/X crawler — API v2 when bearer token set, else demo mode."""

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from configs.settings import settings
from services import system_settings as app_settings
from crawlers.base_crawler import BaseCrawler, CrawledComment, CrawlResult, Platform
from crawlers.instagram.comment_monitor import CommentMonitor


class TwitterCrawler(BaseCrawler):
    DEMO_PHRASES = [
        "Fake journalist, teri reporting band karwa dunga",
        "Roz tweet karunga jab tak delete nahi karti",
        "Tujhe track kar raha hoon",
        "Paid influencer ho tum",
    ]

    def __init__(self, **kwargs) -> None:
        headless = kwargs.pop("headless", None)
        super().__init__(
            platform=Platform.TWITTER,
            storage_path=settings.SCREENSHOTS_PATH / "twitter",
            headless=headless if headless is not None else settings.CRAWLER_HEADLESS,
            timeout_ms=settings.CRAWLER_TIMEOUT_MS,
            **kwargs,
        )

    @property
    def demo_mode(self) -> bool:
        if app_settings.get_crawler_demo_mode():
            return True
        return not bool(settings.TWITTER_BEARER_TOKEN)

    async def setup_session(self) -> bool:
        self._is_running = True
        if self.demo_mode:
            self.logger.info("Twitter crawler in demo mode")
        return True

    async def teardown_session(self) -> None:
        self._is_running = False

    async def _fetch_via_api(
        self,
        target_username: str,
        max_comments: int,
    ) -> List[CrawledComment]:
        token = settings.TWITTER_BEARER_TOKEN
        if not token:
            return []

        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "query": f"@{target_username} -is:retweet lang:en",
            "max_results": min(max_comments, 100),
            "tweet.fields": "created_at,author_id,text",
        }
        comments: List[CrawledComment] = []

        import aiohttp

        async with aiohttp.ClientSession() as client:
            async with client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    self.logger.warning("Twitter API error %s: %s", resp.status, body[:200])
                    return []
                data = await resp.json()
            for item in data.get("data", []):
                text = item.get("text", "")
                if not text or target_username.lower() in text.lower()[:20]:
                    continue
                author = item.get("author_id", "unknown")
                comments.append(
                    CrawledComment(
                        platform=self.platform.value,
                        text=text,
                        accused_username=f"user_{author}",
                        accused_profile_url=f"https://twitter.com/i/user/{author}",
                        target_username=target_username,
                        post_url=f"https://twitter.com/{target_username}",
                        comment_id=str(item.get("id", uuid4().hex[:12])),
                        timestamp=datetime.now(timezone.utc),
                        raw_data={"source": "twitter_api_v2"},
                    )
                )
        return comments[:max_comments]

    async def _fetch_replies_via_api(
        self,
        target_username: str,
        max_comments: int,
    ) -> List[CrawledComment]:
        """Fetch replies directed at the target (conversation monitoring)."""
        token = settings.TWITTER_BEARER_TOKEN
        if not token or max_comments <= 0:
            return []

        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "query": f"to:{target_username} -is:retweet",
            "max_results": min(max_comments, 50),
            "tweet.fields": "created_at,author_id,text,in_reply_to_user_id",
        }
        comments: List[CrawledComment] = []
        import aiohttp

        async with aiohttp.ClientSession() as client:
            async with client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
            for item in data.get("data", []):
                text = item.get("text", "")
                if not text:
                    continue
                author = item.get("author_id", "unknown")
                comments.append(
                    CrawledComment(
                        platform=self.platform.value,
                        text=text,
                        accused_username=f"user_{author}",
                        accused_profile_url=f"https://twitter.com/i/user/{author}",
                        target_username=target_username,
                        post_url=f"https://twitter.com/{target_username}",
                        comment_id=str(item.get("id", uuid4().hex[:12])),
                        timestamp=datetime.now(timezone.utc),
                        raw_data={"source": "twitter_api_v2", "conversation_type": "reply"},
                    )
                )
        return comments

    async def crawl_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int = 100,
    ) -> List[CrawledComment]:
        if self.demo_mode:
            return self._demo_comments(target_username, post_url, max_comments)
        api_comments = await self._fetch_via_api(target_username, max_comments)
        if api_comments:
            reply_comments = await self._fetch_replies_via_api(target_username, max(5, max_comments // 3))
            seen = {c.comment_id for c in api_comments}
            for rc in reply_comments:
                if rc.comment_id not in seen:
                    api_comments.append(rc)
            return api_comments[:max_comments]
        return self._demo_comments(target_username, post_url, min(max_comments, 3))

    def _demo_comments(
        self,
        target_username: str,
        post_url: str,
        max_comments: int,
    ) -> List[CrawledComment]:
        count = min(max_comments, random.randint(2, 4))
        out: List[CrawledComment] = []
        for i in range(count):
            accused = f"x_troll_{random.randint(20, 99)}"
            is_reply = i == 0
            from osint.demo_enrichment import demo_profile_enrichment
            from osint.permaliinks import build_comment_permalink

            cid = f"x_demo_{uuid4().hex[:8]}"
            enrich = demo_profile_enrichment(accused, "twitter")
            enrich["conversation_type"] = "reply" if is_reply else "mention"
            purl = post_url or f"https://twitter.com/{target_username}"
            out.append(
                CrawledComment(
                    platform=self.platform.value,
                    text=random.choice(self.DEMO_PHRASES),
                    accused_username=accused,
                    accused_profile_url=f"https://twitter.com/{accused}",
                    accused_avatar_url=enrich["accused_avatar_url"],
                    target_username=target_username,
                    post_url=purl,
                    comment_id=cid,
                    comment_url=build_comment_permalink(
                        "twitter", username=accused, comment_id=cid, post_url=purl
                    ),
                    timestamp=datetime.now(timezone.utc),
                    raw_data=enrich,
                )
            )
        return out

    async def take_screenshot(
        self,
        url: str,
        element_selector: Optional[str] = None,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        return output_path

    async def crawl_target_profile(
        self,
        target_username: str,
        *,
        max_comments: int = 50,
        known_hashes: Optional[set[str]] = None,
    ) -> CrawlResult:
        started = datetime.now(timezone.utc)
        post_url = f"https://twitter.com/{target_username}"
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
            return CrawlResult(
                platform=self.platform,
                target_username=target_username,
                success=False,
                error=str(exc),
                duration_seconds=duration,
            )
