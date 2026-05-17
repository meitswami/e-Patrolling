"""Facebook Graph API comment fetch (when FACEBOOK_ACCESS_TOKEN is set)."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import httpx

from crawlers.base_crawler import CrawledComment
from utils.logger import get_logger

logger = get_logger(__name__)

GRAPH = "https://graph.facebook.com/v19.0"


async def fetch_profile_comments(
    target_username: str,
    access_token: str,
    *,
    max_comments: int = 50,
) -> List[CrawledComment]:
    """
    Fetch recent comments on a Page's posts via Graph API.
    Works for Facebook Pages (not personal profiles without advanced permissions).
    """
    comments: List[CrawledComment] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        page_resp = await client.get(
            f"{GRAPH}/{target_username}",
            params={"fields": "id,name", "access_token": access_token},
        )
        if page_resp.status_code != 200:
            logger.warning("Graph API page lookup failed: %s", page_resp.text[:200])
            return []

        page_id = page_resp.json().get("id")
        if not page_id:
            return []

        posts_resp = await client.get(
            f"{GRAPH}/{page_id}/posts",
            params={
                "fields": "id,permalink_url",
                "limit": 5,
                "access_token": access_token,
            },
        )
        if posts_resp.status_code != 200:
            return []

        for post in posts_resp.json().get("data", []):
            post_id = post.get("id")
            post_url = post.get("permalink_url") or f"https://facebook.com/{target_username}"
            if not post_id:
                continue

            comm_resp = await client.get(
                f"{GRAPH}/{post_id}/comments",
                params={
                    "fields": "id,message,from,created_time",
                    "limit": min(max_comments, 25),
                    "access_token": access_token,
                },
            )
            if comm_resp.status_code != 200:
                continue

            for row in comm_resp.json().get("data", []):
                text = (row.get("message") or "").strip()
                from_user = row.get("from") or {}
                accused = from_user.get("name") or from_user.get("id") or "unknown"
                accused_id = from_user.get("id", accused)
                if len(text) < 3:
                    continue
                comments.append(
                    CrawledComment(
                        platform="facebook",
                        text=text,
                        accused_username=str(accused).replace(" ", "_")[:64],
                        accused_display_name=str(accused),
                        accused_profile_url=f"https://facebook.com/{accused_id}",
                        target_username=target_username,
                        post_url=post_url,
                        comment_id=row.get("id") or f"fb_api_{uuid4().hex[:8]}",
                        timestamp=datetime.now(timezone.utc),
                        raw_data={"source": "graph_api"},
                    )
                )
                if len(comments) >= max_comments:
                    return comments

    return comments
