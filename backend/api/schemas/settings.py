"""System settings API schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CrawlerSettingsResponse(BaseModel):
    crawler_demo_mode: bool
    instagram_username: str
    instagram_password_set: bool
    instagram_password_configured_in_db: bool
    facebook_email: str = ""
    facebook_password_set: bool = False
    facebook_password_configured_in_db: bool = False
    facebook_access_token_set: bool = False
    threads_uses_instagram_login: bool = True
    evidence_screenshot_mode: str
    source: str


class AiSettingsResponse(BaseModel):
    use_ml_classifier: bool
    use_hf_inference_api: bool
    abuse_confidence_threshold: float
    hf_api_configured: bool
    source: str


class AiSettingsUpdate(BaseModel):
    use_ml_classifier: Optional[bool] = None
    use_hf_inference_api: Optional[bool] = None
    abuse_confidence_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)


class CrawlerSettingsUpdate(BaseModel):
    crawler_demo_mode: Optional[bool] = None
    instagram_username: Optional[str] = Field(None, max_length=255)
    instagram_password: Optional[str] = Field(
        None,
        max_length=512,
        description="Leave empty or send ******** to keep existing password",
    )
    facebook_email: Optional[str] = Field(None, max_length=255)
    facebook_password: Optional[str] = Field(
        None,
        max_length=512,
        description="Leave empty or send ******** to keep existing password",
    )
    evidence_screenshot_mode: Optional[Literal["pillow", "playwright", "both"]] = None
