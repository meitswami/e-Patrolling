# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PATROL portable Windows build

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

REPO = Path(SPECPATH).resolve().parents[1]
APP_NAME = (REPO / "build" / "windows" / "app_name.txt").read_text(encoding="utf-8").strip()
ICON_PATH = REPO / "build" / "windows" / "assets" / "shakti-icon.ico"
VERSION_INFO = REPO / "build" / "windows" / "version_info.txt"
BACKEND_OBF = Path(SPECPATH).resolve() / "dist" / "backend-obf" / "backend"
BACKEND = BACKEND_OBF if BACKEND_OBF.is_dir() else REPO / "backend"
AI_CONFIGS = REPO / "ai_models" / "configs"
UI = REPO / "build" / "windows" / "dist-ui"
STORAGE_SEED = REPO / "storage"

datas = [
    (str(BACKEND), "backend"),
    (str(AI_CONFIGS), "ai_models/configs"),
]
if UI.is_dir():
    datas.append((str(UI), "ui"))

binaries = []

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "playwright",
    "playwright.async_api",
    "asyncpg",
    "redis",
    "passlib.handlers.bcrypt",
]
hiddenimports += collect_submodules("uvicorn")

# Third-party deps used by backend/main.py (not traced: launcher only imports uvicorn;
# backend is shipped as data and loaded at runtime from bundle/backend).
_BACKEND_PACKAGES = (
    "fastapi",
    "starlette",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "asyncpg",
    "redis",
    "multipart",
    "python_multipart",
    "jose",
    "passlib",
    "httpx",
    "httpcore",
    "h11",
    "anyio",
    "sniffio",
    "langdetect",
    "openpyxl",
    "reportlab",
    "PIL",
    "structlog",
    "dateutil",
    "pytz",
    "shortuuid",
    "apscheduler",
    "email_validator",
    "bcrypt",
    "cryptography",
    "greenlet",
    "annotated_types",
    "typing_extensions",
    "dotenv",
    "websockets",
    "watchfiles",
    "httptools",
    "yaml",
)

for _pkg in _BACKEND_PACKAGES:
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:
        hiddenimports.append(_pkg)

a = Analysis(
    [str(REPO / "build" / "windows" / "patrol_launcher.py")],
    pathex=[str(BACKEND)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pandas", "numpy", "torch", "transformers", "tensorflow"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON_PATH) if ICON_PATH.is_file() else None,
    version=str(VERSION_INFO) if VERSION_INFO.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
