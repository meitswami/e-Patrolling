"""Target accounts CRUD."""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.common import PaginatedResponse
from api.schemas.target import TargetCreate, TargetResponse, TargetUpdate
from auth.middleware import get_current_user
from auth.rbac import require_admin, require_analyst
from database.connection import get_session
from crawlers.registry import is_patrol_platform
from database.models import PlatformType, TargetAccount, TargetSource, User

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TargetResponse])
async def list_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    platform: PlatformType | None = None,
    is_active: bool | None = None,
    source: TargetSource | None = None,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[TargetResponse]:
    """List monitored target accounts."""
    query = select(TargetAccount)
    count_query = select(func.count()).select_from(TargetAccount)

    if platform is not None:
        query = query.where(TargetAccount.platform == platform)
        count_query = count_query.where(TargetAccount.platform == platform)
    if is_active is not None:
        query = query.where(TargetAccount.is_active == is_active)
        count_query = count_query.where(TargetAccount.is_active == is_active)
    if source is not None:
        query = query.where(TargetAccount.source == source)
        count_query = count_query.where(TargetAccount.source == source)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    result = await session.execute(
        query.order_by(TargetAccount.created_at.desc()).offset(offset).limit(page_size)
    )
    items = [TargetResponse.model_validate(row) for row in result.scalars().all()]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 1,
    )


@router.post("", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
async def create_target(
    body: TargetCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> TargetResponse:
    """Add a target account to monitor."""
    if not is_patrol_platform(body.platform):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Patrol is not enabled for {body.platform.value}. "
                "Use Instagram, Facebook, Twitter, or Threads."
            ),
        )
    existing = await session.execute(
        select(TargetAccount).where(
            TargetAccount.username == body.username,
            TargetAccount.platform == body.platform,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Target already exists for this username and platform",
        )

    target = TargetAccount(
        **body.model_dump(),
        added_by=current_user.id,
        source=TargetSource.ADMIN_PANEL,
    )
    session.add(target)
    await session.flush()
    await session.refresh(target)
    return TargetResponse.model_validate(target)


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> TargetResponse:
    target = await session.get(TargetAccount, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return TargetResponse.model_validate(target)


@router.patch("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: UUID,
    body: TargetUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> TargetResponse:
    target = await session.get(TargetAccount, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)

    await session.flush()
    await session.refresh(target)
    return TargetResponse.model_validate(target)


@router.post("/{target_id}/reset-crawl-state")
async def reset_target_crawl_state(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
    forget_comments: bool = Query(
        True,
        description="Also delete stored comments/evidence so crawls re-read test comments",
    ),
) -> dict:
    """Clear per-target checkpoint (and optionally comment history) for a fresh crawl."""
    target = await session.get(TargetAccount, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    from services.crawl_checkpoint import clear_target_crawl_state

    return await clear_target_crawl_state(
        session, target_id, forget_stored_comments=forget_comments
    )


@router.post("/reset-crawl-state-all")
async def reset_all_crawl_state(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
    forget_comments: bool = Query(True),
) -> dict:
    """Clear all target checkpoints (testing reset)."""
    from services.crawl_checkpoint import clear_all_crawl_checkpoints

    return await clear_all_crawl_checkpoints(session, forget_stored_comments=forget_comments)


@router.get("/{target_id}/crawl-checkpoint")
async def get_target_crawl_checkpoint(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """Per-target crawl resume state: posts crawled, last comment id/hash per post."""
    target = await session.get(TargetAccount, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    from services.crawl_checkpoint import load_target_checkpoint

    state = await load_target_checkpoint(session, target)
    return {
        "target_id": str(target_id),
        "profile_username": state.profile_username,
        "platform": state.platform,
        "last_run_at": state.last_run_at,
        "pending_posts": len(state.pending_post_urls),
        "posts": [p.to_dict() for p in state.posts.values()],
    }


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> None:
    target = await session.get(TargetAccount, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    await session.delete(target)
