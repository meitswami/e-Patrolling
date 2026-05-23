"""Admin: review website safety requests and convert to monitored targets."""

import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.common import PaginatedResponse
from api.schemas.target import TargetResponse
from api.schemas.website import SafetyRequestResponse, SafetyRequestUpdate
from auth.middleware import get_current_user
from auth.rbac import require_analyst
from crawlers.registry import is_patrol_platform
from database.connection import get_session
from database.models import (
    PlatformType,
    TargetAccount,
    TargetSource,
    User,
    WebsiteRequestStatus,
    WebsiteSafetyRequest,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SafetyRequestResponse])
async def list_website_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: WebsiteRequestStatus | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[SafetyRequestResponse]:
    """List submissions from the public website form."""
    query = select(WebsiteSafetyRequest)
    count_query = select(func.count()).select_from(WebsiteSafetyRequest)
    if status_filter is not None:
        query = query.where(WebsiteSafetyRequest.status == status_filter)
        count_query = count_query.where(WebsiteSafetyRequest.status == status_filter)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    result = await session.execute(
        query.order_by(WebsiteSafetyRequest.created_at.desc()).offset(offset).limit(page_size)
    )
    items = [SafetyRequestResponse.model_validate(r) for r in result.scalars().all()]
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


@router.get("/{request_id}", response_model=SafetyRequestResponse)
async def get_website_request(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> SafetyRequestResponse:
    row = await session.get(WebsiteSafetyRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return SafetyRequestResponse.model_validate(row)


@router.patch("/{request_id}", response_model=SafetyRequestResponse)
async def update_website_request(
    request_id: UUID,
    body: SafetyRequestUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> SafetyRequestResponse:
    row = await session.get(WebsiteSafetyRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if body.status is not None:
        row.status = body.status
        if body.status in (WebsiteRequestStatus.REVIEWED, WebsiteRequestStatus.CONVERTED):
            row.reviewed_at = datetime.now(timezone.utc)
    if body.admin_notes is not None:
        row.admin_notes = body.admin_notes

    await session.flush()
    await session.refresh(row)
    return SafetyRequestResponse.model_validate(row)


@router.post("/{request_id}/convert", response_model=list[TargetResponse])
async def convert_to_targets(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> list[TargetResponse]:
    """Create monitored targets from a website request (source=website_intake)."""
    row = await session.get(WebsiteSafetyRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Request not found")

    created: list[TargetAccount] = []
    region_note = f"Website intake — {row.state}, {row.city}"

    for entry in row.profile_entries or []:
        platform_str = entry.get("platform", "instagram")
        try:
            platform = PlatformType(platform_str)
        except ValueError:
            continue
        if not is_patrol_platform(platform):
            continue

        username = entry.get("username") or ""
        profile_url = entry.get("profile_url") or ""
        if not username or not profile_url:
            continue

        existing = await session.execute(
            select(TargetAccount).where(
                TargetAccount.username == username,
                TargetAccount.platform == platform,
            )
        )
        if existing.scalar_one_or_none():
            continue

        target = TargetAccount(
            username=username,
            platform=platform,
            profile_url=profile_url,
            inferred_region=f"{row.state} — {row.city}",
            notes=region_note,
            added_by=current_user.id,
            source=TargetSource.WEBSITE_INTAKE,
            website_request_id=row.id,
            monitoring_enabled=False,
        )
        session.add(target)
        created.append(target)

    if not created:
        raise HTTPException(
            status_code=400,
            detail="No new targets created (duplicates or unsupported platforms)",
        )

    row.status = WebsiteRequestStatus.CONVERTED
    row.reviewed_at = datetime.now(timezone.utc)
    await session.flush()
    for t in created:
        await session.refresh(t)
    return [TargetResponse.model_validate(t) for t in created]
