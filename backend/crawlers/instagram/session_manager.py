"""Instagram session persistence via Playwright storage state."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

SESSION_FILE = settings.EVIDENCE_STORAGE_PATH.parent / "sessions" / "instagram_state.json"
META_FILE = settings.EVIDENCE_STORAGE_PATH.parent / "sessions" / "instagram_meta.json"


class InstagramSessionManager:
    """Load/save Playwright cookies for authenticated Instagram crawling."""

    def __init__(self, session_path: Optional[Path] = None) -> None:
        self.session_path = session_path or SESSION_FILE
        self.meta_path = META_FILE
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

    def has_saved_session(self) -> bool:
        return self.session_path.is_file() and self.session_path.stat().st_size > 10

    def load_storage_state(self) -> Optional[dict[str, Any]]:
        if not self.has_saved_session():
            return None
        try:
            return json.loads(self.session_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Invalid Instagram session file: %s", exc)
            return None

    def load_meta(self) -> dict[str, Any]:
        if not self.meta_path.is_file():
            return {}
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def save_meta(self, *, username: Optional[str] = None) -> None:
        meta = {
            "username": username or self.load_meta().get("username"),
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        self.meta_path.write_text(json.dumps(meta), encoding="utf-8")

    def get_connected_username(self) -> Optional[str]:
        raw = self.load_meta().get("username")
        return raw.strip() if isinstance(raw, str) and raw.strip() else None

    async def save_storage_state(self, context) -> None:
        """Persist browser context cookies/localStorage."""
        state = await context.storage_state()
        self.session_path.write_text(json.dumps(state), encoding="utf-8")
        logger.info("Instagram session saved to %s", self.session_path)

    def clear_session(self) -> None:
        for path in (self.session_path, self.meta_path):
            try:
                if path.is_file():
                    path.unlink()
            except OSError as exc:
                logger.warning("Could not remove %s: %s", path, exc)
