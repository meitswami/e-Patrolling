"""Threads reuses Instagram session (Meta SSO)."""

from pathlib import Path
from typing import Any, Optional

from configs.settings import settings
from services import system_settings as app_settings

# Shared Meta login — Instagram storage works for threads.net in many cases
SESSION_FILE = settings.EVIDENCE_STORAGE_PATH.parent / "sessions" / "instagram_state.json"


class ThreadsSessionManager:
    def load_storage_state(self) -> Optional[dict[str, Any]]:
        if not SESSION_FILE.exists():
            return None
        import json

        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def has_saved_session(self) -> bool:
        return SESSION_FILE.exists()

    def credentials_configured(self) -> bool:
        return app_settings.instagram_credentials_configured()
