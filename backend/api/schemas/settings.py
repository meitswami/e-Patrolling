"""System settings API schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CrawlerSettingsResponse(BaseModel):
    crawler_demo_mode: bool
    instagram_username: str
    instagram_password_set: bool
    instagram_password_configured_in_db: bool
    evidence_screenshot_mode: str
    source: str


class CrawlerSettingsUpdate(BaseModel):
    crawler_demo_mode: Optional[bool] = None
    instagram_username: Optional[str] = Field(None, max_length=255)
    instagram_password: Optional[str] = Field(
        None,
        max_length=512,
        description="Leave empty or send ******** to keep existing password",
    )
    evidence_screenshot_mode: Optional[Literal["pillow", "playwright", "both"]] = None
