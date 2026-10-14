"""ORM models for Profile Intelligence (per-subject knowledge + change history).

Tracks the MONITORED account's own public profile over time. Does not model
anything about the people who post comments — offender records live in
AccusedProfile / EvidenceReport and are keyed by handle, not de-anonymized.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.models import Base


class TargetProfileKnowledge(Base):
    __tablename__ = "target_profile_knowledge"

    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("target_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    follower_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    following_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    posts_count: Mapped[Optional[int]] = mapped_column(Integer)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_private: Mapped[Optional[bool]] = mapped_column(Boolean)
    public_facts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TargetProfileChange(Base):
    __tablename__ = "target_profile_changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("target_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="crawl")
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
