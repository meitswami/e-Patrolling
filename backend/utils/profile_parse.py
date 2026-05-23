"""Parse social profile URLs or usernames into platform + username."""

import re
from urllib.parse import urlparse

from database.models import PlatformType

_HOST_PLATFORM: dict[str, PlatformType] = {
    "instagram.com": PlatformType.INSTAGRAM,
    "www.instagram.com": PlatformType.INSTAGRAM,
    "facebook.com": PlatformType.FACEBOOK,
    "www.facebook.com": PlatformType.FACEBOOK,
    "m.facebook.com": PlatformType.FACEBOOK,
    "twitter.com": PlatformType.TWITTER,
    "www.twitter.com": PlatformType.TWITTER,
    "x.com": PlatformType.TWITTER,
    "www.x.com": PlatformType.TWITTER,
    "threads.net": PlatformType.THREADS,
    "www.threads.net": PlatformType.THREADS,
}

_SKIP_SEGMENTS = frozenset(
    {"p", "reel", "reels", "stories", "people", "profile.php", "intent", "hashtag"}
)


def parse_profile_input(raw: str) -> tuple[PlatformType, str, str]:
    """
    Return (platform, username, normalized_profile_url).
    Raises ValueError if input cannot be parsed.
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("Profile link or username is required")

    if "://" not in text and "." not in text.split("/")[0]:
        username = text.lstrip("@").split("/")[0].split("?")[0]
        if not username:
            raise ValueError("Invalid username")
        platform = PlatformType.INSTAGRAM
        return platform, username, f"https://www.instagram.com/{username}/"

    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"

    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]

    platform = _HOST_PLATFORM.get(host) or _HOST_PLATFORM.get(f"www.{host}")
    if platform is None:
        raise ValueError(f"Unsupported platform for URL: {host or text}")

    path = (parsed.path or "").strip("/")
    segments = [s for s in path.split("/") if s and s not in _SKIP_SEGMENTS]
    username = ""
    if segments:
        username = segments[-1].lstrip("@")
        if platform == PlatformType.FACEBOOK and segments[0] == "profile.php":
            qs = parsed.query or ""
            m = re.search(r"id=(\d+)", qs)
            username = m.group(1) if m else username

    if not username:
        raise ValueError("Could not extract username from profile URL")

    username = username.split("?")[0]
    if platform == PlatformType.INSTAGRAM:
        url = f"https://www.instagram.com/{username}/"
    elif platform == PlatformType.FACEBOOK:
        url = f"https://www.facebook.com/{username}"
    elif platform == PlatformType.TWITTER:
        url = f"https://x.com/{username}"
    elif platform == PlatformType.THREADS:
        url = f"https://www.threads.net/@{username.lstrip('@')}"
    else:
        url = text
    return platform, username, url
