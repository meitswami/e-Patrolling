"""Target account schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from database.models import PlatformType


class TargetCreate(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    display_name: Optional[str] = None
    platform: PlatformType
    profile_url: str
    avatar_url: Optional[str] = None
    follower_count: Optional[int] = None
    is_verified: bool = False
    monitoring_enabled: bool = True
    crawl_interval_sec: int = Field(default=300, ge=60, le=86400)
    inferred_region: Optional[str] = None
    notes: Optional[str] = None


class TargetUpdate(BaseModel):
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: Optional[int] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    monitoring_enabled: Optional[bool] = None
    crawl_interval_sec: Optional[int] = Field(default=None, ge=60, le=86400)
    inferred_region: Optional[str] = None
    region_confidence: Optional[float] = None
    notes: Optional[str] = None


class TargetResponse(BaseModel):
    id: UUID
    username: str
    display_name: Optional[str]
    platform: PlatformType
    profile_url: str
    avatar_url: Optional[str]
    follower_count: Optional[int]
    is_verified: bool
    is_active: bool
    monitoring_enabled: bool
    crawl_interval_sec: int
    last_crawled_at: Optional[datetime]
    inferred_region: Optional[str]
    region_confidence: Optional[float]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
