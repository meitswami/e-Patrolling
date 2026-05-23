"""Per-target crawl checkpoints — resume posts, incremental comments by ID/hash."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CrawledComment, PlatformType, TargetAccount, TargetCrawlCheckpoint
from utils.logger import get_logger

logger = get_logger(__name__)


def extract_post_id(post_url: str) -> str:
    import re
    from urllib.parse import urlparse

    path = urlparse(post_url).path
    match = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)/?", path)
    return match.group(1) if match else post_url.rstrip("/").split("/")[-1]


@dataclass
class PostCheckpoint:
    post_id: str
    post_url: str
    fully_crawled: bool = False
    last_comment_id: Optional[str] = None
    last_comment_hash: Optional[str] = None
    last_comment_at: Optional[str] = None
    last_accused_username: Optional[str] = None
    comments_seen: int = 0
    known_comment_ids: set[str] = field(default_factory=set)
    known_hashes: set[str] = field(default_factory=set)
    updated_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "post_url": self.post_url,
            "fully_crawled": self.fully_crawled,
            "last_comment_id": self.last_comment_id,
            "last_comment_hash": self.last_comment_hash,
            "last_comment_at": self.last_comment_at,
            "last_accused_username": self.last_accused_username,
            "comments_seen": self.comments_seen,
            "known_comment_ids": sorted(self.known_comment_ids),
            "known_hashes": sorted(self.known_hashes),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PostCheckpoint":
        return cls(
            post_id=data.get("post_id", ""),
            post_url=data.get("post_url", ""),
            fully_crawled=bool(data.get("fully_crawled")),
            last_comment_id=data.get("last_comment_id"),
            last_comment_hash=data.get("last_comment_hash"),
            last_comment_at=data.get("last_comment_at"),
            last_accused_username=data.get("last_accused_username"),
            comments_seen=int(data.get("comments_seen") or 0),
            known_comment_ids=set(data.get("known_comment_ids") or []),
            known_hashes=set(data.get("known_hashes") or []),
            updated_at=data.get("updated_at"),
        )


@dataclass
class TargetCrawlState:
    target_id: UUID
    profile_username: str
    platform: str
    posts: dict[str, PostCheckpoint] = field(default_factory=dict)
    pending_post_urls: list[str] = field(default_factory=list)
    last_run_at: Optional[str] = None

    def get_post(self, post_url: str) -> PostCheckpoint:
        pid = extract_post_id(post_url)
        if pid not in self.posts:
            self.posts[pid] = PostCheckpoint(post_id=pid, post_url=post_url)
        return self.posts[pid]

    def is_post_complete(self, post_url: str) -> bool:
        pid = extract_post_id(post_url)
        post = self.posts.get(pid)
        return bool(post and post.fully_crawled)

    def register_comments(self, post_url: str, comments: list[Any]) -> None:
        """Update checkpoint from newly seen CrawledComment objects."""
        post = self.get_post(post_url)
        now = datetime.now(timezone.utc).isoformat()
        for c in comments:
            if getattr(c, "comment_id", None):
                post.known_comment_ids.add(str(c.comment_id))
            post.known_hashes.add(c.content_hash())
            post.comments_seen += 1
            ts = getattr(c, "timestamp", None)
            if ts:
                post.last_comment_at = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            if getattr(c, "comment_id", None):
                post.last_comment_id = str(c.comment_id)
            if getattr(c, "accused_username", None):
                post.last_accused_username = c.accused_username
            post.last_comment_hash = c.content_hash()
        post.updated_at = now

    def mark_post_complete(self, post_url: str, *, fully: bool = True) -> None:
        post = self.get_post(post_url)
        post.fully_crawled = fully
        post.updated_at = datetime.now(timezone.utc).isoformat()

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "profile_username": self.profile_username,
            "platform": self.platform,
            "last_run_at": self.last_run_at,
            "pending_post_urls": self.pending_post_urls,
            "posts": {pid: p.to_dict() for pid, p in self.posts.items()},
        }

    @classmethod
    def from_storage_dict(
        cls, target_id: UUID, profile_username: str, platform: str, data: dict[str, Any]
    ) -> "TargetCrawlState":
        posts_raw = data.get("posts") or {}
        posts = {pid: PostCheckpoint.from_dict(p) for pid, p in posts_raw.items()}
        return cls(
            target_id=target_id,
            profile_username=profile_username,
            platform=platform,
            posts=posts,
            pending_post_urls=list(data.get("pending_post_urls") or []),
            last_run_at=data.get("last_run_at"),
        )


async def _merge_db_comments(session: AsyncSession, target_id: UUID, state: TargetCrawlState) -> None:
    """Load comment_id + content_hash already stored for this target."""
    result = await session.execute(
        select(
            CrawledComment.post_id,
            CrawledComment.comment_id,
            CrawledComment.content_hash,
            CrawledComment.accused_id,
        ).where(CrawledComment.target_id == target_id)
    )
    for post_id, comment_id, content_hash, _accused in result.all():
        if not post_id:
            continue
        post = state.posts.setdefault(
            post_id,
            PostCheckpoint(post_id=post_id, post_url=f"https://www.instagram.com/p/{post_id}/"),
        )
        if comment_id:
            post.known_comment_ids.add(str(comment_id))
        if content_hash:
            post.known_hashes.add(content_hash)


async def load_target_checkpoint(
    session: AsyncSession,
    target: TargetAccount,
) -> TargetCrawlState:
    """Load persisted checkpoint + merge comments already in DB."""
    result = await session.execute(
        select(TargetCrawlCheckpoint).where(TargetCrawlCheckpoint.target_id == target.id)
    )
    row = result.scalar_one_or_none()
    if row and row.state:
        state = TargetCrawlState.from_storage_dict(
            target.id,
            target.username,
            target.platform.value,
            row.state if isinstance(row.state, dict) else {},
        )
    else:
        state = TargetCrawlState(
            target_id=target.id,
            profile_username=target.username,
            platform=target.platform.value,
        )
    await _merge_db_comments(session, target.id, state)
    return state


async def save_target_checkpoint(
    session: AsyncSession,
    state: TargetCrawlState,
    *,
    flush_only: bool = False,
) -> None:
    """Persist checkpoint (survives backend restart)."""
    state.last_run_at = datetime.now(timezone.utc).isoformat()
    posts_completed = sum(1 for p in state.posts.values() if p.fully_crawled)
    comments_indexed = sum(len(p.known_comment_ids) for p in state.posts.values())

    result = await session.execute(
        select(TargetCrawlCheckpoint).where(TargetCrawlCheckpoint.target_id == state.target_id)
    )
    row = result.scalar_one_or_none()
    payload = state.to_storage_dict()
    if row:
        row.state = payload
        row.profile_username = state.profile_username
        row.posts_completed = posts_completed
        row.comments_indexed = comments_indexed
        row.last_crawl_at = datetime.now(timezone.utc)
    else:
        session.add(
            TargetCrawlCheckpoint(
                target_id=state.target_id,
                platform=PlatformType(state.platform),
                profile_username=state.profile_username,
                state=payload,
                posts_completed=posts_completed,
                comments_indexed=comments_indexed,
                last_crawl_at=datetime.now(timezone.utc),
            )
        )
    if flush_only:
        await session.flush()
    else:
        await session.commit()
    logger.info(
        "Checkpoint saved @%s: %d posts tracked, %d complete, %d comment ids indexed",
        state.profile_username,
        len(state.posts),
        posts_completed,
        comments_indexed,
    )


async def clear_target_crawl_state(
    session: AsyncSession,
    target_id: UUID,
    *,
    forget_stored_comments: bool = False,
) -> dict:
    """
    Reset crawl checkpoint for a target. Optionally delete crawled_comments so
    the next crawl re-reads and re-classifies comments (for testing).
    """
    from sqlalchemy import delete

    from database.models import CrawledComment, EvidenceReport

    result = await session.execute(
        delete(TargetCrawlCheckpoint).where(TargetCrawlCheckpoint.target_id == target_id)
    )
    checkpoints_removed = result.rowcount or 0

    comments_removed = 0
    if forget_stored_comments:
        ev = await session.execute(
            delete(EvidenceReport).where(EvidenceReport.target_id == target_id)
        )
        cr = await session.execute(
            delete(CrawledComment).where(CrawledComment.target_id == target_id)
        )
        comments_removed = cr.rowcount or 0
        _ = ev.rowcount

    await session.commit()
    return {
        "target_id": str(target_id),
        "checkpoints_removed": checkpoints_removed,
        "comments_removed": comments_removed,
        "forget_stored_comments": forget_stored_comments,
    }


async def clear_all_crawl_checkpoints(
    session: AsyncSession,
    *,
    forget_stored_comments: bool = False,
) -> dict:
    """Reset checkpoints for every target (optional: wipe crawled comment rows)."""
    from sqlalchemy import delete

    from database.models import CrawledComment, EvidenceReport

    cp = await session.execute(delete(TargetCrawlCheckpoint))
    comments_removed = 0
    evidence_removed = 0
    if forget_stored_comments:
        evidence_removed = (await session.execute(delete(EvidenceReport))).rowcount or 0
        comments_removed = (await session.execute(delete(CrawledComment))).rowcount or 0
    await session.commit()
    return {
        "checkpoints_removed": cp.rowcount or 0,
        "comments_removed": comments_removed,
        "evidence_removed": evidence_removed,
        "forget_stored_comments": forget_stored_comments,
    }


def build_run_progress_entry(
    post_url: str,
    *,
    new_comments: int,
    stopped_at_known: bool,
    skipped: bool = False,
) -> dict[str, Any]:
    pid = extract_post_id(post_url)
    return {
        "post_id": pid,
        "post_url": post_url,
        "new_comments": new_comments,
        "stopped_at_known_comment": stopped_at_known,
        "skipped_already_complete": skipped,
    }
