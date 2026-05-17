"""Evidence file hashing and chain-of-custody metadata."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def sha256_file(path: Path) -> Optional[str]:
    """Compute SHA-256 hex digest for a file; returns None if missing."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_screenshot_path(relative_path: str, storage_root: Path) -> Path:
    """Map DB-relative screenshot path to absolute filesystem path."""
    root = storage_root.parent
    return root / relative_path.replace("\\", "/").lstrip("/")


def build_chain_entry(
    *,
    collector: str,
    model: str,
    screenshot_path: Optional[str] = None,
    screenshot_hash: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Standard chain-of-custody record stored on evidence_reports."""
    entry: dict[str, Any] = {
        "collector": collector,
        "model": model,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "integrity": "sha256" if screenshot_hash else "text_only",
    }
    if screenshot_path:
        entry["screenshot_path"] = screenshot_path
    if screenshot_hash:
        entry["screenshot_sha256"] = screenshot_hash
    if extra:
        entry.update(extra)
    return entry
