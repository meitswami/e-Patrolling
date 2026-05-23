#!/usr/bin/env python3
"""Download PATROL Hugging Face models into ai_models/cache/."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from configs.settings import settings  # noqa: E402


def _models_from_catalog() -> list[str]:
    catalog_path = ROOT / "ai_models" / "configs" / "models.json"
    if catalog_path.is_file():
        data = json.loads(catalog_path.read_text(encoding="utf-8"))
        return [m["id"] for m in data.get("models", {}).values()]
    return []


def _models_from_settings() -> list[str]:
    ids = [
        settings.MULTILINGUAL_TOXIC_MODEL,
        settings.TOXIC_BERT_MODEL,
        settings.INDIC_ABUSE_MODEL,
    ]
    if settings.USE_INDICBERT:
        ids.append(settings.INDICBERT_MODEL)
    return ids


def main() -> int:
    # Windows: avoid symlink creation (needs Developer Mode / admin).
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "huggingface_hub not installed. Run:\n"
            "  pip install -r requirements-ml-minimal-cpu.txt",
            file=sys.stderr,
        )
        return 1

    cache_dir = settings.MODEL_CACHE_DIR / "hub"
    cache_dir.mkdir(parents=True, exist_ok=True)

    model_ids: list[str] = []
    seen: set[str] = set()
    for mid in _models_from_catalog() + _models_from_settings():
        if mid and mid not in seen:
            seen.add(mid)
            model_ids.append(mid)

    print(f"Cache directory: {cache_dir}")
    print(f"Downloading {len(model_ids)} model(s)...")

    failed: list[str] = []
    for model_id in model_ids:
        print(f"\n>> {model_id}")
        try:
            snapshot_download(repo_id=model_id, cache_dir=str(cache_dir))
            print(f"  OK: {model_id}")
        except Exception as exc:
            failed.append(model_id)
            print(f"  FAILED: {model_id} ({exc})", file=sys.stderr)

    if failed:
        print(
            f"\n{len(failed)} model(s) failed. Re-run this script or set HUGGINGFACE_API_TOKEN in .env.",
            file=sys.stderr,
        )
        return 1

    print("\nAll models downloaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
