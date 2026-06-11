"""Serve exported Next.js UI from FastAPI (portable .exe mode)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from configs.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def mount_portable_ui(app: FastAPI) -> None:
    """Mount static UI and SPA fallback when PATROL_PORTABLE is enabled."""
    ui_root = settings.STATIC_UI_PATH
    if not ui_root:
        ui_root = Path(__file__).resolve().parents[2] / "ui"
    ui_root = Path(ui_root)

    if not ui_root.is_dir():
        logger.warning("Portable UI folder not found: %s", ui_root)
        return

    next_static = ui_root / "_next"
    if next_static.is_dir():
        app.mount("/_next", StaticFiles(directory=str(next_static)), name="next_static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path in ("health", "") or full_path.startswith(
            ("api/", "ws/", "storage/", "docs", "redoc", "openapi.json")
        ):
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")

        clean = full_path.rstrip("/")
        candidate = ui_root / clean if clean else ui_root / "index.html"
        if clean and candidate.is_file():
            return FileResponse(candidate)
        if clean and candidate.is_dir():
            nested = candidate / "index.html"
            if nested.is_file():
                return FileResponse(nested)

        # Dynamic routes pre-built with placeholder param (portable static export)
        dynamic_shells = (
            ("evidence/", ui_root / "evidence" / "_" / "index.html"),
            ("monitoring/log/", ui_root / "monitoring" / "log" / "_" / "index.html"),
            ("offenders/dossier/", ui_root / "offenders" / "dossier" / "_" / "index.html"),
        )
        for prefix, shell in dynamic_shells:
            if clean.startswith(prefix):
                if shell.is_file():
                    return FileResponse(shell)
                break

        index = ui_root / "index.html"
        if index.is_file():
            return FileResponse(index)

        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="UI not found")

    logger.info("Portable UI mounted from %s", ui_root)
