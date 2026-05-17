"""Build direct permalinks to posts and comments (preserved on evidence records)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote


def build_comment_permalink(
    platform: str,
    *,
    username: str,
    post_id: str = "",
    comment_id: str = "",
    post_url: str = "",
    comment_url: Optional[str] = None,
) -> Optional[str]:
    """Return a direct URL to the comment/thread when possible."""
    if comment_url and comment_url.startswith("http"):
        return comment_url

    plat = platform.lower()
    user = username.lstrip("@")
    pid = post_id or ""
    cid = comment_id or ""

    if plat == "instagram" and user and pid:
        if cid:
            return f"https://www.instagram.com/p/{pid}/c/{cid}/"
        return post_url or f"https://www.instagram.com/p/{pid}/"

    if plat == "twitter" and cid:
        return f"https://twitter.com/i/status/{cid}"

    if plat == "facebook" and post_url:
        if cid and "comment_id=" not in post_url:
            sep = "&" if "?" in post_url else "?"
            return f"{post_url}{sep}comment_id={cid}"
        return post_url

    if plat == "threads" and user:
        if cid:
            return f"https://www.threads.net/@{quote(user)}/post/{cid}"
        return post_url or f"https://www.threads.net/@{quote(user)}"

    return post_url or None


def build_permalink_snapshot(
    *,
    platform: str,
    username: str,
    post_url: Optional[str],
    comment_url: Optional[str],
    post_id: Optional[str],
    comment_id: Optional[str],
    comment_posted_at: Optional[str],
    captured_at: Optional[str] = None,
    raw_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Immutable permalink bundle stored on evidence for deletion-resilient records."""
    permalink = build_comment_permalink(
        platform,
        username=username,
        post_id=post_id or "",
        comment_id=comment_id or "",
        post_url=post_url or "",
        comment_url=comment_url,
    )
    return {
        "platform": platform,
        "username": username,
        "post_url": post_url,
        "comment_url": comment_url or permalink,
        "direct_comment_link": permalink,
        "post_id": post_id,
        "comment_id": comment_id,
        "comment_posted_at": comment_posted_at,
        "archived_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "deletion_note": (
            "If the comment is removed on-platform, this PATROL record retains "
            "screenshot hash, capture time, and archived text."
        ),
        "raw_network": (raw_data or {}).get("network_hints"),
    }
