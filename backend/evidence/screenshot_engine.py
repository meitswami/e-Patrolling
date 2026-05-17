"""Evidence screenshot artifacts — Pillow cards and optional Playwright page capture."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from configs.settings import settings
from services import system_settings as app_settings
from utils.logger import get_logger

if TYPE_CHECKING:
    from crawlers.base_crawler import BaseCrawler

logger = get_logger(__name__)


def _evidence_path(platform: str, evidence_id: str) -> Path:
    now = datetime.now(timezone.utc)
    folder = (
        settings.EVIDENCE_STORAGE_PATH
        / platform
        / str(now.year)
        / f"{now.month:02d}"
        / f"{now.day:02d}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{evidence_id}.png"


def _relative_storage_path(path: Path) -> str:
    rel = path.relative_to(settings.EVIDENCE_STORAGE_PATH.parent)
    return str(rel).replace("\\", "/")


def capture_evidence_screenshot(
    *,
    evidence_id: str,
    platform: str,
    comment_text: str,
    accused_username: str,
    target_username: str,
    severity: str,
    post_url: Optional[str] = None,
    comment_url: Optional[str] = None,
    comment_posted_at: Optional[str] = None,
) -> Optional[str]:
    """
    Create a PNG evidence card. Returns path relative to storage root for DB.
    Uses Pillow (no browser required).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — skipping screenshot")
        return None

    path = _evidence_path(platform, evidence_id)
    width, height = 900, 420
    img = Image.new("RGB", (width, height), color=(18, 18, 24))
    draw = ImageDraw.Draw(img)

    try:
        font_lg = ImageFont.truetype("arial.ttf", 22)
        font_sm = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font_lg = ImageFont.load_default()
        font_sm = font_lg

    draw.rectangle([(0, 0), (width, 48)], fill=(0, 200, 150))
    draw.text((16, 12), f"PATROL Evidence · {evidence_id}", fill=(0, 0, 0), font=font_lg)
    draw.text((16, 60), f"Platform: {platform}  |  Severity: {severity}", fill=(180, 220, 200), font=font_sm)
    draw.text(
        (16, 88),
        f"Target: @{target_username}  |  Accused: @{accused_username}",
        fill=(200, 200, 210),
        font=font_sm,
    )

    preview = (comment_text or "")[:280]
    y = 120
    for line in _wrap_text(preview, 95):
        draw.text((16, y), line, fill=(240, 240, 245), font=font_sm)
        y += 22

    link = comment_url or post_url
    if link:
        draw.text((16, height - 54), f"Link: {link[:85]}", fill=(120, 140, 160), font=font_sm)
    if comment_posted_at:
        draw.text(
            (16, height - 36),
            f"Comment posted: {comment_posted_at[:22]}",
            fill=(120, 140, 160),
            font=font_sm,
        )
    draw.text(
        (16, height - 18),
        f"Archived: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        fill=(100, 110, 120),
        font=font_sm,
    )

    img.save(path, format="PNG")
    rel = _relative_storage_path(path)
    logger.info("Evidence screenshot saved: %s", rel)
    return rel


async def capture_playwright_screenshot(
    crawler: BaseCrawler,
    *,
    url: str,
    evidence_id: str,
    platform: str,
) -> Optional[str]:
    """
    Capture a browser screenshot via an open crawler session.
    Returns storage-relative path or None.
    """
    if not url or getattr(crawler, "demo_mode", True):
        return None

    path = _evidence_path(platform, f"{evidence_id}_page")
    try:
        saved = await crawler.take_screenshot(url, output_path=path)
    except Exception as exc:
        logger.warning("Playwright evidence screenshot failed: %s", exc)
        return None

    if not saved or not saved.exists() or saved.stat().st_size < 100:
        if saved and saved.exists():
            saved.unlink(missing_ok=True)
        return None

    rel = _relative_storage_path(saved)
    logger.info("Playwright evidence screenshot saved: %s", rel)
    return rel


async def capture_evidence_artifacts(
    crawler: Optional[BaseCrawler],
    *,
    evidence_id: str,
    platform: str,
    comment_text: str,
    accused_username: str,
    target_username: str,
    severity: str,
    post_url: Optional[str] = None,
    page_url: Optional[str] = None,
    comment_url: Optional[str] = None,
    comment_posted_at: Optional[str] = None,
    demo_mode: bool = False,
) -> Optional[str]:
    """
    Build evidence image(s) per EVIDENCE_SCREENSHOT_MODE.
    Returns primary path for DB (prefers Playwright page capture when available).
    """
    if not settings.CAPTURE_EVIDENCE_SCREENSHOTS:
        return None

    mode = app_settings.get_evidence_screenshot_mode()
    pillow_path: Optional[str] = None
    playwright_path: Optional[str] = None

    if mode in ("pillow", "both"):
        pillow_path = capture_evidence_screenshot(
            evidence_id=evidence_id,
            platform=platform,
            comment_text=comment_text,
            accused_username=accused_username,
            target_username=target_username,
            severity=severity,
            post_url=post_url,
            comment_url=comment_url,
            comment_posted_at=comment_posted_at,
        )

    if mode in ("playwright", "both") and crawler and not demo_mode:
        shot_url = page_url or post_url
        if shot_url:
            playwright_path = await capture_playwright_screenshot(
                crawler,
                url=shot_url,
                evidence_id=evidence_id,
                platform=platform,
            )

    if mode == "playwright":
        return playwright_path or pillow_path
    if mode == "both":
        return playwright_path or pillow_path
    return pillow_path


def _wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        if len(test) <= width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [""]
