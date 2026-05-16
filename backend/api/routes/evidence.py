"""Evidence reports API."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.schemas.common import PaginatedResponse
from api.schemas.evidence import EvidenceDetail, EvidenceListItem
from auth.middleware import get_current_user
from database.connection import get_session
from database.models import AccusedProfile, EvidenceReport, PlatformType, SeverityLevel, TargetAccount, User

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EvidenceListItem])
async def list_evidence(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: PlatformType | None = None,
    severity: SeverityLevel | None = None,
    is_escalated: bool | None = None,
    search: str | None = Query(None, max_length=200),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[EvidenceListItem]:
    """Paginated evidence list with optional filters."""
    TargetAlias = aliased(TargetAccount)
    AccusedAlias = aliased(AccusedProfile)

    base = (
        select(
            EvidenceReport,
            TargetAlias.username.label("target_username"),
            AccusedAlias.username.label("accused_username"),
        )
        .outerjoin(TargetAlias, EvidenceReport.target_id == TargetAlias.id)
        .outerjoin(AccusedAlias, EvidenceReport.accused_id == AccusedAlias.id)
    )

    count_q = select(func.count()).select_from(EvidenceReport)

    if platform is not None:
        base = base.where(EvidenceReport.platform == platform)
        count_q = count_q.where(EvidenceReport.platform == platform)
    if severity is not None:
        base = base.where(EvidenceReport.severity_level == severity)
        count_q = count_q.where(EvidenceReport.severity_level == severity)
    if is_escalated is not None:
        base = base.where(EvidenceReport.is_escalated == is_escalated)
        count_q = count_q.where(EvidenceReport.is_escalated == is_escalated)
    if search:
        pattern = f"%{search}%"
        base = base.where(
            or_(
                EvidenceReport.comment_text.ilike(pattern),
                EvidenceReport.evidence_id.ilike(pattern),
            )
        )
        count_q = count_q.where(
            or_(
                EvidenceReport.comment_text.ilike(pattern),
                EvidenceReport.evidence_id.ilike(pattern),
            )
        )

    total = await session.scalar(count_q) or 0
    offset = (page - 1) * page_size
    rows = await session.execute(
        base.order_by(EvidenceReport.created_at.desc()).offset(offset).limit(page_size)
    )

    items: list[EvidenceListItem] = []
    for evidence, target_username, accused_username in rows.all():
        item = EvidenceListItem.model_validate(evidence)
        item.target_username = target_username
        item.accused_username = accused_username
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


@router.get("/{evidence_id}", response_model=EvidenceDetail)
async def get_evidence(
    evidence_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> EvidenceDetail:
    """Get single evidence report by UUID."""
    TargetAlias = aliased(TargetAccount)
    AccusedAlias = aliased(AccusedProfile)

    row = await session.execute(
        select(
            EvidenceReport,
            TargetAlias.username,
            AccusedAlias.username,
        )
        .outerjoin(TargetAlias, EvidenceReport.target_id == TargetAlias.id)
        .outerjoin(AccusedAlias, EvidenceReport.accused_id == AccusedAlias.id)
        .where(EvidenceReport.id == evidence_id)
    )
    result = row.one_or_none()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    evidence, target_username, accused_username = result
    detail = EvidenceDetail.model_validate(evidence)
    detail.target_username = target_username
    detail.accused_username = accused_username
    return detail
