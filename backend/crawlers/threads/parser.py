"""Parse Threads profile HTML into CrawledComment objects."""

import json
import re
from datetime import datetime, timezone
from typing import List

from crawlers.base_crawler import CrawledComment

_THREADS_TEXT_USER = re.compile(
    r'"text"\s*:\s*"([^"]{4,500})".*?"username"\s*:\s*"([^"]{1,64})"',
    re.DOTALL,
)
_POST_CAPTION = re.compile(
    r'"post_text"\s*:\s*"([^"]{4,500})".*?"username"\s*:\s*"([^"]{1,64})"',
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
    target_username: str,
    post_url: str,
    max_comments: int = 50,
) -> List[CrawledComment]:
    """Best-effort extraction from threads.net profile HTML."""
    comments: List[CrawledComment] = []
    seen: set[str] = set()

    for pattern in (_THREADS_TEXT_USER, _POST_CAPTION):
        for match in pattern.finditer(html):
            text = _decode_escaped(match.group(1)).strip()
            username = match.group(2).strip()
            if len(text) < 4 or username.lower() == target_username.lower():
                continue
            key = f"{username}:{text[:80]}"
            if key in seen:
                continue
            seen.add(key)
            comments.append(
                CrawledComment(
                    platform="threads",
                    text=text,
                    accused_username=username,
                    accused_profile_url=f"https://www.threads.net/@{username}",
                    target_username=target_username,
                    post_url=post_url,
                    comment_id=f"th_{hash(key) & 0xFFFFFFFF:08x}",
                    timestamp=datetime.now(timezone.utc),
                    raw_data={"source": "threads_html_parse"},
                )
            )
            if len(comments) >= max_comments:
                return comments

    return comments
