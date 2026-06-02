"""Discovery API — auto-discovered targets list, export, and manual trigger."""

import csv
import io
import math
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.rbac import require_admin, require_analyst
from database.connection import get_session
from database.models import User
from database.models_discovery import DiscoveredTarget, DiscoveryRun
from services.discovery_crawler import convert_discovered_to_target, run_discovery

router = APIRouter()


# ── List discovered targets (date-wise) ─────────────────────

@router.get("")
async def list_discovered_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    run_date: date | None = None,
    platform: str | None = None,
    region: str | None = None,
    is_converted: bool | None = None,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> dict:
    """List discovered targets with date-wise filtering and pagination."""
    query = select(DiscoveredTarget)
    count_query = select(func.count()).select_from(DiscoveredTarget)

    if run_date is not None:
        query = query.where(DiscoveredTarget.discovered_on == run_date)
        count_query = count_query.where(DiscoveredTarget.discovered_on == run_date)
    if platform:
        query = query.where(DiscoveredTarget.platform == platform)
        count_query = count_query.where(DiscoveredTarget.platform == platform)
    if region:
        query = query.where(DiscoveredTarget.inferred_region.ilike(f"%{region}%"))
        count_query = count_query.where(DiscoveredTarget.inferred_region.ilike(f"%{region}%"))
    if is_converted is not None:
        query = query.where(DiscoveredTarget.is_converted == is_converted)
        count_query = count_query.where(DiscoveredTarget.is_converted == is_converted)

    total = await session.scalar(count_query) or 0
    offset = (page - 1) * page_size
    result = await session.execute(
        query.order_by(DiscoveredTarget.discovered_on.desc(), DiscoveredTarget.follower_count.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = []
    for dt in result.scalars().all():
        items.append({
            "id": str(dt.id),
            "platform": dt.platform.value,
            "username": dt.username,
            "display_name": dt.display_name,
            "profile_url": dt.profile_url,
            "avatar_url": dt.avatar_url,
            "bio": dt.bio,
            "follower_count": dt.follower_count,
            "is_verified": dt.is_verified,
            "gender": dt.gender,
            "inferred_region": dt.inferred_region,
            "region_confidence": dt.region_confidence,
            "discovered_on": dt.discovered_on.isoformat(),
            "is_converted": dt.is_converted,
            "is_dismissed": dt.is_dismissed,
            "created_at": dt.created_at.isoformat() if dt.created_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)) if total else 1,
    }


# ── List discovery runs ──────────────────────────────────────

@router.get("/runs")
async def list_discovery_runs(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[dict]:
    """List discovery run history."""
    result = await session.execute(
        select(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(limit)
    )
    items = []
    for run in result.scalars().all():
        items.append({
            "id": str(run.id),
            "run_date": run.run_date.isoformat(),
            "platforms": run.platforms or [],
            "total_found": run.total_found,
            "total_converted": run.total_converted,
            "status": run.status,
            "error_message": run.error_message,
            "triggered_by": run.triggered_by,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        })
    return items


# ── Trigger discovery manually ───────────────────────────────

@router.post("/run")
async def trigger_discovery(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
) -> dict:
    """Manually trigger a discovery run."""
    run = await run_discovery(session, triggered_by="manual")
    return {
        "status": "completed",
        "run_id": str(run.id),
        "total_found": run.total_found,
        "message": f"Discovery complete: {run.total_found} new profiles found",
    }


# ── Convert discovered target to monitored target ────────────

@router.post("/{discovered_id}/convert")
async def convert_to_target(
    discovered_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> dict:
    """Convert a discovered profile into a monitored target account."""
    try:
        target = await convert_discovered_to_target(session, discovered_id, current_user.id)
        return {
            "status": "converted",
            "target_id": str(target.id),
            "username": target.username,
            "platform": target.platform.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ── Dismiss discovered target ────────────────────────────────

@router.post("/{discovered_id}/dismiss")
async def dismiss_discovered(
    discovered_id: UUID,
    reason: str = Query("", description="Optional reason for dismissal"),
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> dict:
    """Mark a discovered profile as dismissed (not relevant)."""
    dt = await session.get(DiscoveredTarget, discovered_id)
    if not dt:
        raise HTTPException(status_code=404, detail="Discovered target not found")
    dt.is_dismissed = True
    dt.dismissed_reason = reason or None
    await session.commit()
    return {"status": "dismissed", "id": str(discovered_id)}


# ── Export discovered targets as Excel ───────────────────────

@router.get("/export.xlsx")
async def export_discovered_excel(
    run_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> StreamingResponse:
    """Export discovered targets as Excel file."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
    except ImportError:
        # Fallback to CSV if openpyxl not installed
        return await _export_discovered_csv(run_date, session)

    query = select(DiscoveredTarget)
    if run_date:
        query = query.where(DiscoveredTarget.discovered_on == run_date)
    query = query.order_by(DiscoveredTarget.discovered_on.desc(), DiscoveredTarget.follower_count.desc())
    result = await session.execute(query.limit(5000))

    wb = Workbook()
    ws = wb.active
    ws.title = "Discovered Targets"

    # Header
    headers = [
        "Date", "Platform", "Username", "Display Name", "Profile URL",
        "Followers", "Verified", "Gender", "Region", "Region Confidence",
        "Bio", "Converted", "Status",
    ]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, dt in enumerate(result.scalars().all(), 2):
        ws.cell(row=row_idx, column=1, value=dt.discovered_on.isoformat())
        ws.cell(row=row_idx, column=2, value=dt.platform.value)
        ws.cell(row=row_idx, column=3, value=dt.username)
        ws.cell(row=row_idx, column=4, value=dt.display_name or "")
        ws.cell(row=row_idx, column=5, value=dt.profile_url)
        ws.cell(row=row_idx, column=6, value=dt.follower_count)
        ws.cell(row=row_idx, column=7, value="Yes" if dt.is_verified else "No")
        ws.cell(row=row_idx, column=8, value=dt.gender)
        ws.cell(row=row_idx, column=9, value=dt.inferred_region or "")
        ws.cell(row=row_idx, column=10, value=round(dt.region_confidence or 0, 2))
        ws.cell(row=row_idx, column=11, value=(dt.bio or "")[:200])
        ws.cell(row=row_idx, column=12, value="Yes" if dt.is_converted else "No")
        ws.cell(row=row_idx, column=13, value="Converted" if dt.is_converted else ("Dismissed" if dt.is_dismissed else "Pending"))

    # Auto-width columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    date_label = run_date.isoformat() if run_date else "all"
    filename = f"shakti_discovered_targets_{date_label}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.csv")
async def export_discovered_csv_route(
    run_date: date | None = None,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> StreamingResponse:
    """Export discovered targets as CSV file."""
    return await _export_discovered_csv(run_date, session)


async def _export_discovered_csv(
    run_date: date | None,
    session: AsyncSession,
) -> StreamingResponse:
    """Internal CSV export helper."""
    query = select(DiscoveredTarget)
    if run_date:
        query = query.where(DiscoveredTarget.discovered_on == run_date)
    query = query.order_by(DiscoveredTarget.discovered_on.desc(), DiscoveredTarget.follower_count.desc())
    result = await session.execute(query.limit(5000))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Date", "Platform", "Username", "Display Name", "Profile URL",
        "Followers", "Verified", "Gender", "Region", "Bio", "Converted",
    ])
    for dt in result.scalars().all():
        writer.writerow([
            dt.discovered_on.isoformat(),
            dt.platform.value,
            dt.username,
            dt.display_name or "",
            dt.profile_url,
            dt.follower_count,
            "Yes" if dt.is_verified else "No",
            dt.gender,
            dt.inferred_region or "",
            (dt.bio or "")[:200],
            "Yes" if dt.is_converted else "No",
        ])

    content = buffer.getvalue().encode("utf-8-sig")
    date_label = run_date.isoformat() if run_date else "all"
    filename = f"shakti_discovered_targets_{date_label}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
