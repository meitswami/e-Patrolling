"""Evidence reports API."""

import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.schemas.common import PaginatedResponse
from api.schemas.evidence import (
    EvidenceBackfillResponse,
    EvidenceDetail,
    EvidenceEscalateRequest,
    EvidenceEscalateResponse,
    EvidenceListItem,
)
from auth.middleware import get_current_user
from auth.rbac import require_admin, require_analyst
from configs.settings import settings
from database.connection import get_session
from api.helpers.evidence_abuse import apply_evidence_abuse_fields
from services.evidence_backfill import backfill_evidence_abuse_categories
from database.models import (
    AIResult,
    AccusedProfile,
    EvidenceReport,
    PlatformType,
    SeverityLevel,
    TargetAccount,
    User,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[EvidenceListItem])
async def list_evidence(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: PlatformType | None = None,
    severity: SeverityLevel | None = None,
    is_escalated: bool | None = None,
    search: str | None = Query(None, max_length=200),
    target_id: str | None = Query(None, description="Filter by target account UUID"),
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
            AIResult,
        )
        .outerjoin(TargetAlias, EvidenceReport.target_id == TargetAlias.id)
        .outerjoin(AccusedAlias, EvidenceReport.accused_id == AccusedAlias.id)
        .outerjoin(AIResult, EvidenceReport.ai_result_id == AIResult.id)
    )

    count_q = select(func.count()).select_from(EvidenceReport)

    if target_id:
        try:
            target_uuid = UUID(target_id)
            base = base.where(EvidenceReport.target_id == target_uuid)
            count_q = count_q.where(EvidenceReport.target_id == target_uuid)
        except ValueError:
            pass
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
    for evidence, target_username, accused_username, ai_row in rows.all():
        item = EvidenceListItem.model_validate(evidence)
        item.target_username = target_username
        item.accused_username = accused_username
        apply_evidence_abuse_fields(item, evidence, ai_row)
        items.append(item)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


@router.post("/backfill-categories", response_model=EvidenceBackfillResponse)
async def backfill_evidence_categories(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> EvidenceBackfillResponse:
    """One-click backfill of abuse category labels on all stored evidence."""
    result = await backfill_evidence_abuse_categories(session)
    return EvidenceBackfillResponse(**result)


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
            AIResult,
        )
        .outerjoin(TargetAlias, EvidenceReport.target_id == TargetAlias.id)
        .outerjoin(AccusedAlias, EvidenceReport.accused_id == AccusedAlias.id)
        .outerjoin(AIResult, EvidenceReport.ai_result_id == AIResult.id)
        .where(EvidenceReport.id == evidence_id)
    )
    result = row.one_or_none()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    evidence, target_username, accused_username, ai_row = result
    detail = EvidenceDetail.model_validate(evidence)
    detail.target_username = target_username
    detail.accused_username = accused_username
    apply_evidence_abuse_fields(detail, evidence, ai_row)
    return detail


@router.get("/{evidence_id}/screenshot")
async def get_evidence_screenshot(
    evidence_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Serve evidence PNG from storage."""
    evidence = await session.get(EvidenceReport, evidence_id)
    if not evidence or not evidence.screenshot_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found")
    root = settings.EVIDENCE_STORAGE_PATH.parent
    path = root / evidence.screenshot_path.replace("\\", "/")
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file missing")
    return FileResponse(path, media_type="image/png", filename=path.name)


@router.post("/{evidence_id}/escalate", response_model=EvidenceEscalateResponse)
async def escalate_evidence(
    evidence_id: UUID,
    body: EvidenceEscalateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> EvidenceEscalateResponse:
    """Mark evidence as escalated for law-enforcement review."""
    evidence = await session.get(EvidenceReport, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    now = datetime.now(timezone.utc)
    evidence.is_escalated = True
    evidence.escalated_at = now
    if body.notes:
        evidence.notes = body.notes.strip()
    custody = dict(evidence.chain_of_custody or {})
    custody["escalated_by"] = str(current_user.id)
    custody["escalated_by_email"] = current_user.email
    evidence.chain_of_custody = custody

    await session.flush()
    return EvidenceEscalateResponse(
        id=evidence.id,
        evidence_id=evidence.evidence_id,
        is_escalated=evidence.is_escalated,
        escalated_at=evidence.escalated_at or now,
        notes=evidence.notes,
    )


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> None:
    """Permanently delete evidence (admin only)."""
    evidence = await session.get(EvidenceReport, evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    if evidence.screenshot_path:
        root = settings.EVIDENCE_STORAGE_PATH.parent
        path = root / evidence.screenshot_path.replace("\\", "/")
        if path.is_file():
            path.unlink(missing_ok=True)

    await session.delete(evidence)
