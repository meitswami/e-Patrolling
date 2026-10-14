"""Historical Instagram crawl — older posts and comments on each post."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urlparse

from configs.settings import settings
from crawlers.base_crawler import CrawledComment
from crawlers.instagram.parser import parse_comments_from_html, parse_shared_data_json
from services.crawl_checkpoint import extract_post_id

_POST_PATH = re.compile(r"/(?:p|reel)/([A-Za-z0-9_-]+)/?")

# Instagram UI strings for expanding the full comment thread (EN + common variants).
# Hidden-comment toggles come FIRST: Instagram collapses comments it flags as
# "offensive or spam" behind a "See/View hidden comments" control, and those are
# exactly the abusive comments this platform exists to detect. They must be
# revealed before the thread is parsed or they never enter the DOM.
_HIDDEN_LABELS = (
    "See hidden comments",
    "View hidden comments",
    "See hidden comment",
    "View hidden comment",
    "छिपी हुई टिप्पणियाँ देखें",
)
_EXPAND_LABELS = _HIDDEN_LABELS + (
    "View all comments",
    "View more comments",
    "Load more comments",
    "Show more comments",
    "Show more",
    "View more replies",
    "View replies",
    "Load more replies",
    "See more comments",
    "और टिप्पणियाँ देखें",
    "और देखें",
)

# Descriptive, non-clickable text that sits next to the hidden-comments toggle
# ("These comments were hidden because they may be offensive or spam."). Never
# treat it as a button — matching it would waste a click and can swallow errors.
_NON_CLICKABLE_HINTS = ("were hidden because", "may be offensive")


def _normalize_post_url(href: str, username: str) -> str | None:
    if not href:
        return None
    if href.startswith("/"):
        href = f"https://www.instagram.com{href}"
    parsed = urlparse(href)
    if "instagram.com" not in parsed.netloc:
        return None
    if not _POST_PATH.search(parsed.path):
        return None
    path = parsed.path.rstrip("/") + "/"
    return f"https://www.instagram.com{path}"


async def _scroll_comment_panel(page, rounds: int, delay_sec: float) -> None:
    """Scroll inside the post modal / comment list so lazy-loaded comments appear."""
    for _ in range(rounds):
        await page.evaluate(
            """
            () => {
              const pick = (sel) => Array.from(document.querySelectorAll(sel));
              const candidates = [
                ...pick('div[role="dialog"] ul'),
                ...pick('div[role="dialog"]'),
                ...pick('article ul'),
                ...pick('article'),
              ];
              const el = candidates.find((n) => n.scrollHeight > n.clientHeight + 40)
                || document.documentElement;
              el.scrollTop = el.scrollHeight;
            }
            """
        )
        await asyncio.sleep(delay_sec)


async def _expand_comment_thread(page, max_rounds: int) -> int:
    """
    Repeatedly click 'View all / Load more / Show more' until none appear.
    Returns number of successful expand clicks.
    """
    clicks = 0
    for _ in range(max_rounds):
        clicked_this_round = False
        for label in _EXPAND_LABELS:
            try:
                btn = page.get_by_role("button", name=label, exact=False).first
                if not await btn.is_visible(timeout=400):
                    btn = page.get_by_text(label, exact=False).first
                if await btn.is_visible(timeout=400):
                    # Guard: never click the descriptive "these comments were
                    # hidden because…" paragraph that sits beside the toggle.
                    try:
                        txt = ((await btn.inner_text()) or "").lower()
                    except Exception:
                        txt = ""
                    if any(h in txt for h in _NON_CLICKABLE_HINTS):
                        continue
                    await btn.click()
                    clicks += 1
                    clicked_this_round = True
                    # Hidden-comment reveals are slower to render than a plain
                    # "load more"; give them a touch longer to populate the DOM.
                    await asyncio.sleep(1.2 if label in _HIDDEN_LABELS else 0.8)
            except Exception:
                continue
        await _scroll_comment_panel(page, rounds=2, delay_sec=0.6)
        if not clicked_this_round:
            break
    return clicks


async def collect_post_urls(
    page,
    username: str,
    max_posts: int,
    scroll_rounds: int,
    *,
    crawl_target_id: str | None = None,
) -> List[str]:
    """Scroll profile grid and collect unique post/reel URLs."""
    from services.crawl_pause import check_crawl_pause

    profile_url = f"https://www.instagram.com/{username}/"
    await page.goto(profile_url, wait_until="domcontentloaded")
    await asyncio.sleep(2.0)

    scroll_delay = settings.HISTORICAL_CRAWL_PROFILE_SCROLL_DELAY_SEC
    found: Set[str] = set()
    for _ in range(scroll_rounds):
        await check_crawl_pause(crawl_target_id)
        hrefs: List[str] = await page.eval_on_selector_all(
            'a[href*="/p/"], a[href*="/reel/"]',
            "els => els.map(e => e.getAttribute('href')).filter(Boolean)",
        )
        for href in hrefs:
            url = _normalize_post_url(href, username)
            if url:
                found.add(url)
            if len(found) >= max_posts:
                break
        if len(found) >= max_posts:
            break
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(scroll_delay)

    return list(found)[:max_posts]


@dataclass
class PostCrawlOutcome:
    comments: List[CrawledComment]
    stopped_at_known: bool
    expand_clicks: int


def _enrich_parsed(
    comments: List[CrawledComment],
    post_url: str,
    post_id: str,
    *,
    expand_clicks: int,
) -> List[CrawledComment]:
    for c in comments:
        c.post_url = post_url
        c.post_id = post_id
        c.raw_data = {
            **(c.raw_data or {}),
            "crawl_type": "historical",
            "post_url": post_url,
            "post_id": post_id,
            "expand_clicks": expand_clicks,
        }
    return comments


def _parse_page_comments(
    html: str,
    *,
    target_username: str,
    post_url: str,
    max_comments: int,
) -> List[CrawledComment]:
    comments = parse_comments_from_html(
        html,
        platform="instagram",
        target_username=target_username,
        post_url=post_url,
        max_comments=max_comments,
    )
    if len(comments) >= max_comments // 2:
        return comments
    for script_text in re.findall(
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    ):
        try:
            import json

            data = json.loads(script_text)
            extra = parse_shared_data_json(
                data,
                platform="instagram",
                target_username=target_username,
                post_url=post_url,
                max_comments=max_comments - len(comments),
            )
            seen = {f"{c.accused_username}:{c.text[:80]}" for c in comments}
            for c in extra:
                key = f"{c.accused_username}:{c.text[:80]}"
                if key not in seen:
                    comments.append(c)
                    seen.add(key)
        except Exception:
            continue
        if len(comments) >= max_comments:
            break
    return comments


def _collect_incremental(
    batch: List[CrawledComment],
    *,
    known_comment_ids: set[str],
    known_hashes: set[str],
    seen_keys: set[str],
) -> tuple[List[CrawledComment], bool]:
    """
    Collect genuinely new comments from a batch, skipping already-indexed ones.

    Unlike the previous implementation that broke at the first known comment
    (assuming newest-first ordering), this version scans the ENTIRE batch and
    collects all comments that are not yet known. Instagram does NOT guarantee
    strict reverse-chronological ordering after expanding threads — older
    comments can appear before newer ones, so we must not stop early.

    The `hit_known` flag is still returned for informational/checkpoint purposes
    (indicates the crawler has overlap with previously indexed content).
    """
    new_items: List[CrawledComment] = []
    hit_known = False
    for c in batch:
        dedupe = f"{c.accused_username}:{c.text[:80]}"
        if dedupe in seen_keys:
            continue
        cid = (c.comment_id or "").strip()
        ch = c.content_hash()
        if (cid and cid in known_comment_ids) or ch in known_hashes:
            hit_known = True
            # Don't break — continue scanning for new comments that may
            # appear after known ones in the DOM (Instagram ordering is not
            # guaranteed to be strictly newest-first after thread expansion).
            continue
        new_items.append(c)
        seen_keys.add(dedupe)
    return new_items, hit_known


async def crawl_post_comments(
    page,
    post_url: str,
    target_username: str,
    max_comments: int,
    rate_limit_wait,
    *,
    known_comment_ids: Optional[set[str]] = None,
    known_hashes: Optional[set[str]] = None,
    incremental: bool = True,
    crawl_target_id: str | None = None,
) -> PostCrawlOutcome:
    """Open post, expand comments; collect new comments not in known set."""
    from services.crawl_pause import check_crawl_pause

    post_id = extract_post_id(post_url)
    known_ids = known_comment_ids or set()
    known_hashes_set = known_hashes or set()
    use_incremental = incremental and (bool(known_ids) or bool(known_hashes_set))

    await page.goto(post_url, wait_until="domcontentloaded")
    await rate_limit_wait(1.5)

    expand_rounds = settings.HISTORICAL_CRAWL_COMMENT_EXPAND_ROUNDS
    scroll_rounds = settings.HISTORICAL_CRAWL_COMMENT_SCROLL_ROUNDS
    expand_clicks = 0
    all_new: List[CrawledComment] = []
    seen_keys: set[str] = set()
    stopped_at_known = False

    if use_incremental:
        prev_new_count = 0
        stall_rounds = 0
        for round_idx in range(expand_rounds):
            await check_crawl_pause(crawl_target_id)
            if round_idx == 0:
                expand_clicks += await _expand_comment_thread(page, 3)
            else:
                clicks = await _expand_comment_thread(page, 2)
                expand_clicks += clicks
                if clicks == 0 and round_idx > 2:
                    break
            await _scroll_comment_panel(page, max(2, scroll_rounds // 2), delay_sec=0.5)
            html = await page.content()
            batch = _parse_page_comments(
                html,
                target_username=target_username,
                post_url=post_url,
                max_comments=max_comments,
            )
            new_batch, hit = _collect_incremental(
                batch,
                known_comment_ids=known_ids,
                known_hashes=known_hashes_set,
                seen_keys=seen_keys,
            )
            all_new.extend(new_batch)
            if hit:
                stopped_at_known = True
            # Stop expanding when we're not finding new comments anymore.
            # This replaces the old "break on first known" logic which missed
            # new comments appearing after known ones in the DOM.
            if len(all_new) == prev_new_count:
                stall_rounds += 1
                if stall_rounds >= 2:
                    # Two consecutive rounds with no new comments — done
                    break
            else:
                stall_rounds = 0
                prev_new_count = len(all_new)
            if len(all_new) >= max_comments:
                break
    else:
        expand_clicks = await _expand_comment_thread(page, expand_rounds)
        await _scroll_comment_panel(page, scroll_rounds, delay_sec=0.7)
        html = await page.content()
        all_new = _parse_page_comments(
            html,
            target_username=target_username,
            post_url=post_url,
            max_comments=max_comments,
        )

    trimmed = _enrich_parsed(all_new[:max_comments], post_url, post_id, expand_clicks=expand_clicks)
    return PostCrawlOutcome(
        comments=trimmed,
        stopped_at_known=stopped_at_known,
        expand_clicks=expand_clicks,
    )
