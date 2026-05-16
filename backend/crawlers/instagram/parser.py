"""Parse Instagram HTML/embedded JSON into CrawledComment objects."""

import json
import re
from datetime import datetime, timezone
from typing import Any, List, Optional

from crawlers.base_crawler import CrawledComment

_COMMENT_BLOCK = re.compile(
    r'"text"\s*:\s*"([^"]{4,500})".*?"username"\s*:\s*"([^"]{1,64})"',
    re.DOTALL,
)


def _decode_escaped(text: str) -> str:
    try:
        return json.loads(f'"{text}"')
    except json.JSONDecodeError:
        return text.replace("\\n", "\n").replace('\\"', '"')


def parse_comments_from_html(
    html: str,
    *,
    platform: str,
    target_username: str,
    post_url: str,
    max_comments: int = 50,
) -> List[CrawledComment]:
    """
    Best-effort extraction from public page HTML / embedded JSON blobs.
    Instagram changes often; returns partial results.
    """
    comments: List[CrawledComment] = []
    seen: set[str] = set()

    for match in _COMMENT_BLOCK.finditer(html):
        text = _decode_escaped(match.group(1)).strip()
        username = match.group(2).strip()
        if not text or username.lower() == target_username.lower():
            continue
        key = f"{username}:{text[:80]}"
        if key in seen:
            continue
        seen.add(key)
        comment_id = f"ig_{hash(key) & 0xFFFFFFFF:08x}"
        comments.append(
            CrawledComment(
                platform=platform,
                text=text,
                accused_username=username,
                accused_profile_url=f"https://www.instagram.com/{username}/",
                target_username=target_username,
                post_url=post_url,
                comment_id=comment_id,
                timestamp=datetime.now(timezone.utc),
                raw_data={"source": "html_parse"},
            )
        )
        if len(comments) >= max_comments:
            break

    return comments


def parse_shared_data_json(payload: Any, **kwargs) -> List[CrawledComment]:
    """Walk Instagram __additionalDataLoaded / GraphQL-shaped dicts."""
    comments: List[CrawledComment] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = node.get("text")
            user = node.get("user") or node.get("owner")
            if isinstance(text, str) and len(text) > 3 and isinstance(user, dict):
                username = user.get("username")
                if username:
                    comments.append(
                        CrawledComment(
                            platform=kwargs.get("platform", "instagram"),
                            text=text,
                            accused_username=username,
                            accused_profile_url=f"https://www.instagram.com/{username}/",
                            target_username=kwargs.get("target_username", ""),
                            post_url=kwargs.get("post_url", ""),
                            comment_id=str(node.get("id", f"ig_{len(comments)}")),
                            timestamp=datetime.now(timezone.utc),
                            raw_data={"source": "json_walk"},
                        )
                    )
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return comments[: kwargs.get("max_comments", 50)]
