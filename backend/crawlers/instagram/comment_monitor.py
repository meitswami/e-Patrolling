"""Detect new comments since last crawl via content hashes."""

from typing import Iterable, Set

from crawlers.base_crawler import CrawledComment


class CommentMonitor:
    """Tracks seen comment hashes to return only new items."""

    def __init__(self, known_hashes: Iterable[str] | None = None) -> None:
        self._seen: Set[str] = set(known_hashes or [])

    def filter_new(self, comments: list[CrawledComment]) -> list[CrawledComment]:
        fresh: list[CrawledComment] = []
        for comment in comments:
            digest = comment.content_hash()
            if digest in self._seen:
                continue
            self._seen.add(digest)
            fresh.append(comment)
        return fresh

    @property
    def seen_count(self) -> int:
        return len(self._seen)
