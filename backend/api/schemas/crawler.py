"""Crawler API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    log_id: Optional[str] = None
    historical: bool = False
    posts_crawled: int = 0
    success: bool
    comments_new: int = 0
    abusive_detected: int = 0
    critical_detected: int = 0
    duration_seconds: Optional[float] = None
    evidence_ids: List[str] = []
    error: Optional[str] = None


class RunningCrawlInfo(BaseModel):
    target_id: str
    target_username: str
    platform: str
    started_at: str
    mode: str


class CrawlLogEvidenceItem(BaseModel):
    evidence_id: str
    uuid: UUID
    accused_username: Optional[str] = None
    severity: str
    risk_score: int
    comment_preview: str
    screenshot_path: Optional[str] = None
    abuse_categories: List[str] = []
    is_abusive: bool = True
    is_lexicon_match: bool = False
    abuse_explanations: List[Dict[str, Any]] = []


class CrawlLogResultsResponse(BaseModel):
    log_id: UUID
    target_id: Optional[UUID] = None
    target_username: Optional[str] = None
    platform: str
    success: bool
    comments_new: int
    abusive_detected: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    evidence: List[CrawlLogEvidenceItem] = []


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
    mode: str = "live"
    instagram_credentials_configured: bool = False
    running_targets: List[RunningCrawlInfo] = []
    scheduler_is_running: bool = False
    scheduler_last_run_at: Optional[str] = None
    scheduler_last_run_status: Optional[str] = None
    scheduler_last_run_message: Optional[str] = None
    evidence_screenshot_mode: str = "both"
    crawl_stop_requested: bool = False
    recent_errors: List[Dict[str, Any]] = []
    last_export_at: Optional[str] = None
    last_export_path: Optional[str] = None


class MonitoringLogItem(BaseModel):
    id: UUID
    target_id: Optional[UUID]
    target_username: Optional[str] = None
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
