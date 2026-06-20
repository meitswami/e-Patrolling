"""
SQLAlchemy ORM models — mirrors backend/database/schema.sql.
Use Alembic for changes after initial deploy; schema.sql remains bootstrap source.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Enums (match PostgreSQL types in schema.sql) ─────────────────


class PlatformType(str, enum.Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


# PostgreSQL platform_type uses lowercase values; bind enum .value not .name
_PLATFORM_PG = Enum(
    PlatformType,
    name="platform_type",
    values_callable=lambda members: [m.value for m in members],
)


class SeverityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LanguageType(str, enum.Enum):
    HINDI = "hindi"
    ENGLISH = "english"
    HINGLISH = "hinglish"
    UNKNOWN = "unknown"


_LANGUAGE_PG = Enum(
    LanguageType,
    name="language_type",
    values_callable=lambda members: [m.value for m in members],
)


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class OffenderStatus(str, enum.Enum):
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"
    ESCALATED = "ESCALATED"
    REPORTED = "REPORTED"


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class TargetSource(str, enum.Enum):
    ADMIN_PANEL = "admin_panel"
    WEBSITE_INTAKE = "website_intake"


class WebsiteRequestStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    CONVERTED = "converted"
    DISMISSED = "dismissed"


_TARGET_SOURCE_PG = Enum(
    TargetSource,
    name="target_source",
    values_callable=lambda members: [m.value for m in members],
)

_WEBSITE_REQUEST_STATUS_PG = Enum(
    WebsiteRequestStatus,
    name="website_request_status",
    values_callable=lambda members: [m.value for m in members],
)


# ── Models ───────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.ANALYST)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TargetAccount(Base):
    __tablename__ = "target_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    follower_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    crawl_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    inferred_region: Mapped[Optional[str]] = mapped_column(String(255))
    region_confidence: Mapped[Optional[float]] = mapped_column(Float)
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[TargetSource] = mapped_column(
        _TARGET_SOURCE_PG, default=TargetSource.ADMIN_PANEL, nullable=False
    )
    website_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WebsiteSafetyRequest(Base):
    __tablename__ = "website_safety_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    profile_entries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WebsiteRequestStatus] = mapped_column(
        _WEBSITE_REQUEST_STATUS_PG, default=WebsiteRequestStatus.PENDING, nullable=False
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class AccusedProfile(Base):
    __tablename__ = "accused_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    avatar_hash: Mapped[Optional[str]] = mapped_column(String(64))
    osint_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    osint_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    follower_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    following_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    account_age_days: Mapped[Optional[int]] = mapped_column(Integer)
    total_incidents: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    max_risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[OffenderStatus] = mapped_column(
        Enum(OffenderStatus, name="offender_status"), default=OffenderStatus.SUSPECTED
    )
    is_repeat_offender: Mapped[bool] = mapped_column(Boolean, default=False)
    inferred_region: Mapped[Optional[str]] = mapped_column(String(255))
    region_confidence: Mapped[Optional[float]] = mapped_column(Float)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrawledComment(Base):
    __tablename__ = "crawled_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[Optional[str]] = mapped_column(String(255))
    comment_id: Mapped[Optional[str]] = mapped_column(String(255))
    comment_url: Mapped[Optional[str]] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[LanguageType] = mapped_column(
        _LANGUAGE_PG, default=LanguageType.UNKNOWN
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("target_accounts.id")
    )
    accused_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accused_profiles.id")
    )
    platform_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ai_result: Mapped[Optional["AIResult"]] = relationship(back_populates="comment", uselist=False)


class AIResult(Base):
    __tablename__ = "ai_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawled_comments.id", ondelete="CASCADE"), nullable=False
    )
    is_abusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sexual_harassment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rape_threat: Mapped[bool] = mapped_column(Boolean, default=False)
    is_stalking: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hate_speech: Mapped[bool] = mapped_column(Boolean, default=False)
    is_threat: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bullying: Mapped[bool] = mapped_column(Boolean, default=False)
    is_doxxing: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    toxicity_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    severity_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level"), default=SeverityLevel.LOW
    )
    detected_language: Mapped[LanguageType] = mapped_column(
        _LANGUAGE_PG, default=LanguageType.UNKNOWN
    )
    matched_keywords: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    detected_entities: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    model_used: Mapped[Optional[str]] = mapped_column(String(100))
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comment: Mapped["CrawledComment"] = relationship(back_populates="ai_result")


class EvidenceReport(Base):
    __tablename__ = "evidence_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crawled_comments.id")
    )
    ai_result_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_results.id")
    )
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("target_accounts.id")
    )
    accused_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accused_profiles.id")
    )
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    post_url: Mapped[Optional[str]] = mapped_column(Text)
    comment_url: Mapped[Optional[str]] = mapped_column(Text)
    platform_comment_id: Mapped[Optional[str]] = mapped_column(String(255))
    post_id: Mapped[Optional[str]] = mapped_column(String(255))
    permalink_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    comment_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    severity_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level"), nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    screenshot_path: Mapped[Optional[str]] = mapped_column(Text)
    screenshot_hash: Mapped[Optional[str]] = mapped_column(String(64))
    capture_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    captured_by_user: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    chain_of_custody: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    verification_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RepeatOffender(Base):
    __tablename__ = "repeat_offenders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accused_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accused_profiles.id"), unique=True, nullable=False
    )
    total_offenses: Mapped[int] = mapped_column(Integer, default=0)
    targets_harassed: Mapped[int] = mapped_column(Integer, default=0)
    platforms_used: Mapped[Optional[List[PlatformType]]] = mapped_column(
        ARRAY(_PLATFORM_PG), default=list
    )
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    first_offense_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_offense_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[OffenderStatus] = mapped_column(
        Enum(OffenderStatus, name="offender_status"), default=OffenderStatus.CONFIRMED
    )
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    flagged_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TargetCrawlCheckpoint(Base):
    """Persistent per-target crawl position (posts + comment IDs) for resume/incremental."""

    __tablename__ = "target_crawl_checkpoints"

    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("target_accounts.id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    profile_username: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    posts_completed: Mapped[int] = mapped_column(Integer, default=0)
    comments_indexed: Mapped[int] = mapped_column(Integer, default=0)
    last_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("target_accounts.id")
    )
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    comments_found: Mapped[int] = mapped_column(Integer, default=0)
    comments_new: Mapped[int] = mapped_column(Integer, default=0)
    abusive_detected: Mapped[int] = mapped_column(Integer, default=0)
    critical_detected: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    pages_crawled: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    crawl_progress: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    crawl_mode: Mapped[Optional[str]] = mapped_column(String(32))
    session_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RegionScore(Base):
    __tablename__ = "region_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accused_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accused_profiles.id"), nullable=False
    )
    city: Mapped[Optional[str]] = mapped_column(String(255))
    district: Mapped[Optional[str]] = mapped_column(String(255))
    state: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100), default="India")
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    detection_signals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DashboardEvent(Base):
    __tablename__ = "dashboard_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    hour_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    platform: Mapped[Optional[PlatformType]] = mapped_column(_PLATFORM_PG)
    severity_level: Mapped[Optional[SeverityLevel]] = mapped_column(
        Enum(SeverityLevel, name="severity_level")
    )
    region: Mapped[Optional[str]] = mapped_column(String(255))
    event_count: Mapped[int] = mapped_column(Integer, default=1)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SystemSetting(Base):
    """Key-value system configuration (admin UI); secrets stored encrypted."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), default=ReportStatus.PENDING
    )
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
