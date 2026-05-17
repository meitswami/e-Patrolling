"""Hash profile pictures for cross-platform OSINT matching."""

from __future__ import annotations

import hashlib
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def hash_avatar_url_fallback(avatar_url: str) -> str:
    """Weak hash when image cannot be downloaded (URL-only fingerprint)."""
    return hashlib.sha256(f"url:{avatar_url}".encode()).hexdigest()


async def compute_avatar_hash(avatar_url: Optional[str]) -> Optional[str]:
    """
    SHA-256 of avatar image bytes for same-DP detection across platforms.
    Falls back to URL hash if download fails.
    """
    if not avatar_url or not avatar_url.startswith("http"):
        return None

    try:
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(avatar_url) as resp:
                if resp.status != 200:
                    return hash_avatar_url_fallback(avatar_url)
                data = await resp.read()
                if len(data) < 32:
                    return hash_avatar_url_fallback(avatar_url)
                return hashlib.sha256(data).hexdigest()
    except Exception as exc:
        logger.debug("Avatar download failed for OSINT hash: %s", exc)
        return hash_avatar_url_fallback(avatar_url)
