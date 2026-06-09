"""
SQLAlchemy ORM models for auto-discovery feature.
Appended to models.py concepts but kept separate to avoid circular imports.
"""

import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models import Base, PlatformType, _PLATFORM_PG


class DiscoveredTarget(Base):
    __tablename__ = "discovered_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[PlatformType] = mapped_column(_PLATFORM_PG, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    follower_count: Mapped[int] = mapped_column(BigInteger, default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    gender: Mapped[str] = mapped_column(String(20), default="female")
    inferred_region: Mapped[Optional[str]] = mapped_column(String(255))
    region_confidence: Mapped[Optional[float]] = mapped_column(Float)
    region_raw: Mapped[Optional[str]] = mapped_column(Text)
    discovered_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    discovery_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    discovery_criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    converted_to_target_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("target_accounts.id", ondelete="SET NULL")
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    platforms: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), default=list)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    total_converted: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    triggered_by: Mapped[str] = mapped_column(String(50), default="scheduler")


class DiscoverySchedule(Base):
    __tablename__ = "discovery_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interval: Mapped[str] = mapped_column(String(50), default="daily")
    custom_cron: Mapped[Optional[str]] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    options: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
