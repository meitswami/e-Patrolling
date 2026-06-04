"""Discovery API request/response schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DiscoveryRunOptions(BaseModel):
    """Configurable options for a discovery run."""
    max_count: int = Field(default=25, ge=1, le=500)
    min_followers: int = Field(default=10000, ge=0)
    max_followers: Optional[int] = Field(default=None, ge=0)
    gender: Literal["female", "male", "all"] = "female"
    require_verified: bool = True
    regions: Optional[list[str]] = None
    hashtags: Optional[list[str]] = None
    content_types: Optional[list[str]] = None
    platforms: Optional[list[str]] = None


class DiscoveryScheduleRequest(BaseModel):
    """Request model for updating discovery schedule."""
    interval: Literal["manual", "daily", "weekly", "every_6h", "custom"] = "daily"
    custom_cron: Optional[str] = None
    enabled: bool = True


class DiscoveryScheduleResponse(BaseModel):
    """Response model for discovery schedule."""
    interval: str = "daily"
    custom_cron: Optional[str] = None
    enabled: bool = True
    next_run_at: Optional[str] = None
