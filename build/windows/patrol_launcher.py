"""
PATROL portable launcher — starts API + opens browser.
Entry point for PyInstaller e-Patrol.exe build.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _resolve_paths() -> tuple[Path, Path]:
    if getattr(sys, "frozen", False):
        bundle = Path(sys._MEIPASS)
        exe_dir = Path(sys.executable).resolve().parent
        return bundle, exe_dir
    repo = Path(__file__).resolve().parents[2]
    return repo, repo


def _configure_env(bundle: Path, exe_dir: Path) -> None:
    os.environ.setdefault("PATROL_PORTABLE", "1")
    os.environ.setdefault("ENVIRONMENT", "production")
    os.environ.setdefault("CRAWLER_SCHEDULER_ENABLED", "false")
    os.environ.setdefault("REDIS_ENABLED", "false")
    os.environ.setdefault("USE_ML_CLASSIFIER", "false")
    os.environ.setdefault("PRELOAD_AI_MODELS", "false")

    env_file = exe_dir / ".env"
    if env_file.is_file():
        os.environ["PATROL_ENV_FILE"] = str(env_file)
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=True)
        except ImportError:
            pass

    browsers = exe_dir / "playwright-browsers"
    if browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)

    storage = exe_dir / "storage"
    storage.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("EVIDENCE_STORAGE_PATH", str(storage / "evidence"))
    os.environ.setdefault("SCREENSHOTS_PATH", str(storage / "screenshots"))
    os.environ.setdefault("EXPORTS_PATH", str(storage / "exports"))
    os.environ.setdefault("LOGS_PATH", str(storage / "logs"))

    ui = bundle / "ui"
    if ui.is_dir():
        os.environ.setdefault("STATIC_UI_PATH", str(ui))

    backend = bundle / "backend"
    if backend.is_dir():
        sys.path.insert(0, str(backend))
    else:
        sys.path.insert(0, str(bundle))


def _start_server(port: int) -> None:
    import uvicorn

    from main import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        workers=1,
    )


def _configure_console_utf8() -> None:
    """Avoid UnicodeEncodeError on Windows cp1252 consoles."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> None:
    bundle, exe_dir = _resolve_paths()
    _configure_console_utf8()
    _configure_env(bundle, exe_dir)
    os.chdir(str(bundle / "backend" if (bundle / "backend").is_dir() else bundle))

    port = int(os.environ.get("PORTABLE_PORT", "8765"))
    url = f"http://127.0.0.1:{port}"

    server = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server.start()

    for _ in range(40):
        try:
            import urllib.request

            urllib.request.urlopen(f"{url}/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    webbrowser.open(f"{url}/admin")
    print(f"Shakti - the 3rd Eye running at {url} - close this window to stop.")
    try:
        while server.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
