"""Facebook session persistence via Playwright storage state."""

import json
from pathlib import Path
from typing import Any, Optional

from configs.settings import settings
from services import system_settings as app_settings
from utils.logger import get_logger

logger = get_logger(__name__)

SESSION_FILE = settings.EVIDENCE_STORAGE_PATH.parent / "sessions" / "facebook_state.json"


class FacebookSessionManager:
    def load_storage_state(self) -> Optional[dict[str, Any]]:
        if not SESSION_FILE.exists():
            return None
        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load Facebook session: %s", exc)
            return None

    async def save_storage_state(self, context) -> None:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = await context.storage_state()
        SESSION_FILE.write_text(json.dumps(state), encoding="utf-8")
        logger.info("Facebook session saved to %s", SESSION_FILE)

    def has_saved_session(self) -> bool:
        return SESSION_FILE.exists()

    def credentials_configured(self) -> bool:
        return app_settings.facebook_credentials_configured()
