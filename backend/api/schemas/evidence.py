"""Evidence report schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from database.models import PlatformType, SeverityLevel


class EvidenceListItem(BaseModel):
    id: UUID
    evidence_id: str
    platform: PlatformType
    comment_text: str
    severity_level: SeverityLevel
    risk_score: int
    capture_timestamp: datetime
    created_at: datetime
    is_escalated: bool
    screenshot_path: Optional[str]
    target_username: Optional[str] = None
    accused_username: Optional[str] = None

    model_config = {"from_attributes": True}


class EvidenceDetail(EvidenceListItem):
    post_url: Optional[str]
    comment_timestamp: Optional[datetime]
    notes: Optional[str]
    escalated_at: Optional[datetime] = None
    target_id: Optional[UUID]
    accused_id: Optional[UUID]


class EvidenceEscalateRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)


class EvidenceEscalateResponse(BaseModel):
    id: UUID
    evidence_id: str
    is_escalated: bool
    escalated_at: datetime
    notes: Optional[str]


class EvidenceFilters(BaseModel):
    platform: Optional[PlatformType] = None
    severity: Optional[SeverityLevel] = None
    is_escalated: Optional[bool] = None
    search: Optional[str] = Field(default=None, max_length=200)
