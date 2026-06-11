"""Convert Shakti logo PNG to multi-size Windows .ico for PyInstaller."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
PNG = ROOT / "assets" / "shakti-logo.png"
ICO = ROOT / "assets" / "shakti-icon.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> None:
    if not PNG.is_file():
        raise SystemExit(f"Logo not found: {PNG}")

    img = Image.open(PNG).convert("RGBA")
    # Square crop from center for crisp taskbar/desktop icons
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    master = img.resize((256, 256), Image.Resampling.LANCZOS)
    master.save(ICO, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Wrote {ICO} ({ICO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
