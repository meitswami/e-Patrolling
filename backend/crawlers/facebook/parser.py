"""Parse Facebook page HTML into CrawledComment objects."""

import json
import re
from datetime import datetime, timezone
from typing import List

from crawlers.base_crawler import CrawledComment

# Embedded JSON comment bodies (common in FB web)
_FB_COMMENT_JSON = re.compile(
    r'"body"\s*:\s*\{"text"\s*:\s*"([^"]{4,800})"\}.*?"name"\s*:\s*"([^"]{1,120})"',
    re.DOTALL,
)
_FB_COMMENT_ALT = re.compile(
    r'"message"\s*:\s*\{"text"\s*:\s*"([^"]{4,800})"\}.*?"name"\s*:\s*"([^"]{1,120})"',
    re.DOTALL,
)
# aria-label="Comment by User. ..."
_ARIA_COMMENT = re.compile(
    r'aria-label="Comment by ([^".]{1,64})[^"]*".*?>([^<]{4,500})<',
    re.DOTALL | re.IGNORECASE,
)


def _decode_escaped(text: str) -> str:
    try:
        return json.loads(f'"{text}"')
    except json.JSONDecodeError:
        return text.replace("\\n", "\n").replace('\\"', '"').replace("\\u0027", "'")


def parse_comments_from_html(
    html: str,
    *,
    target_username: str,
    post_url: str,
    max_comments: int = 50,
) -> List[CrawledComment]:
    """Best-effort extraction from Facebook profile/post HTML."""
    comments: List[CrawledComment] = []
    seen: set[str] = set()

    def add(text: str, username: str, source: str) -> None:
        text = _decode_escaped(text).strip()
        username = username.strip()
        if len(text) < 4 or username.lower() == target_username.lower():
            return
        key = f"{username}:{text[:80]}"
        if key in seen:
            return
        seen.add(key)
        slug = username.replace(" ", ".")
        comments.append(
            CrawledComment(
                platform="facebook",
                text=text,
                accused_username=slug,
                accused_profile_url=f"https://www.facebook.com/{slug}",
                target_username=target_username,
                post_url=post_url,
                comment_id=f"fb_{hash(key) & 0xFFFFFFFF:08x}",
                timestamp=datetime.now(timezone.utc),
                raw_data={"source": source},
            )
        )

    for pattern, source in (
        (_FB_COMMENT_JSON, "fb_json_body"),
        (_FB_COMMENT_ALT, "fb_json_message"),
    ):
        for match in pattern.finditer(html):
            add(match.group(1), match.group(2), source)
            if len(comments) >= max_comments:
                return comments

    for match in _ARIA_COMMENT.finditer(html):
        add(match.group(2), match.group(1), "fb_aria")
        if len(comments) >= max_comments:
            break

    return comments[:max_comments]
