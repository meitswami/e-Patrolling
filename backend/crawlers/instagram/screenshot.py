"""Screenshot helpers for Instagram evidence capture."""

from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


async def capture_page_screenshot(page, output_path: Path, *, full_page: bool = False) -> Optional[Path]:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output_path), full_page=full_page)
        return output_path
    except Exception as exc:
        logger.warning("Screenshot failed: %s", exc)
        return None


async def capture_element_screenshot(page, selector: str, output_path: Path) -> Optional[Path]:
    try:
        element = page.locator(selector).first
        if await element.count() == 0:
            return None
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await element.screenshot(path=str(output_path))
        return output_path
    except Exception as exc:
        logger.warning("Element screenshot failed: %s", exc)
        return None
