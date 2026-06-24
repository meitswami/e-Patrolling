#!/usr/bin/env python3
"""Quick Playwright launch test on VPS."""
import asyncio
import os
from playwright.async_api import async_playwright


async def main() -> None:
    print("DISPLAY=", os.environ.get("DISPLAY"))
    for headless in (True, False):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                await browser.close()
            print(f"headless={headless}: OK")
        except Exception as exc:
            print(f"headless={headless}: FAIL {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
