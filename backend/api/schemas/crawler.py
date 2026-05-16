"""Crawler API schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from database.models import PlatformType


class CrawlTriggerResponse(BaseModel):
    status: str
    target_id: Optional[UUID] = None
    message: str


class CrawlResultSummary(BaseModel):
    target_id: str
    target_username: Optional[str] = None
    platform: Optional[str] = None
    success: bool
    comments_new: int = 0
    abusive_detected: int = 0
    critical_detected: int = 0
    duration_seconds: Optional[float] = None
    demo_mode: Optional[bool] = None
    error: Optional[str] = None


class PlatformPatrolInfo(BaseModel):
    id: str
    label: str
    status: str  # active | roadmap
    patrol_enabled: bool
    target_count: int = 0
    monitoring_count: int = 0


class CrawlerStatusResponse(BaseModel):
    supported_platforms: List[str]
    platforms: List[PlatformPatrolInfo]
    redis_enabled: bool
    scheduler_enabled: bool
    crawl_interval_seconds: int
    demo_mode: bool
    scheduler_is_running: bool = False
    scheduler_last_run_at: Optional[str] = None
    scheduler_last_run_status: Optional[str] = None
    scheduler_last_run_message: Optional[str] = None
    evidence_screenshot_mode: str = "both"


class MonitoringLogItem(BaseModel):
    id: UUID
    target_id: Optional[UUID]
    platform: PlatformType
    comments_found: int
    comments_new: int
    abusive_detected: int
    critical_detected: int
    success: bool
    error_message: Optional[str]
    duration_seconds: Optional[float]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
