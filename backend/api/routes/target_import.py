"""Bulk import targets from Excel + sample template download."""

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.middleware import get_current_user
from auth.rbac import require_analyst
from crawlers.registry import is_patrol_platform
from database.connection import get_session
from database.models import PlatformType, TargetAccount, TargetSource, User
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Expected Excel columns (matching sample template)
TEMPLATE_COLUMNS = [
    "username",
    "display_name",
    "platform",
    "profile_url",
    "follower_count",
    "is_verified",
    "gender",
    "region",
    "notes",
]

SAMPLE_ROWS = [
    [
        "priyanka_sharma",
        "Priyanka Sharma",
        "instagram",
        "https://instagram.com/priyanka_sharma",
        150000,
        "Yes",
        "female",
        "Mumbai",
        "Bollywood actress",
    ],
    [
        "anjali_verma",
        "Anjali Verma",
        "twitter",
        "https://twitter.com/anjali_verma",
        80000,
        "Yes",
        "female",
        "Delhi",
        "News anchor",
    ],
    [
        "sneha_influencer",
        "Sneha K",
        "instagram",
        "https://instagram.com/sneha_influencer",
        45000,
        "No",
        "female",
        "Bangalore",
        "Tech influencer",
    ],
]


# ── Download sample Excel template ───────────────────────────

@router.get("/template.xlsx")
async def download_import_template(
    _user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Download a sample Excel template for bulk target import."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="openpyxl required. Install: pip install openpyxl",
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Targets"

    # Header styling
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Write headers
    for col, h in enumerate(TEMPLATE_COLUMNS, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    # Write sample data
    for row_idx, row_data in enumerate(SAMPLE_ROWS, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border

    # Instructions sheet
    ws_info = wb.create_sheet("Instructions")
    instructions = [
        ["Shakti - Bulk Target Import Template"],
        [""],
        ["Column", "Required", "Description", "Valid Values"],
        ["username", "YES", "Social media handle (without @)", "Text, max 255 chars"],
        ["display_name", "No", "Full display name", "Text"],
        ["platform", "YES", "Social media platform", "instagram, twitter, facebook, threads"],
        ["profile_url", "YES", "Full profile URL", "Valid URL starting with https://"],
        ["follower_count", "No", "Number of followers", "Integer (e.g. 50000)"],
        ["is_verified", "No", "Blue tick / verified badge", "Yes or No"],
        ["gender", "No", "Gender of the account holder", "female, male, unknown"],
        ["region", "No", "State/City detected from bio", "Text (e.g. Mumbai, Delhi)"],
        ["notes", "No", "Any admin notes", "Text"],
        [""],
        ["NOTES:"],
        ["1. First row must be the header (column names as shown above)"],
        ["2. username + platform must be unique (duplicates will be skipped)"],
        ["3. Platform must be one of: instagram, twitter, facebook, threads"],
        ["4. Maximum 500 rows per import"],
        ["5. Import will skip rows with missing required fields (username, platform, profile_url)"],
    ]
    for row_idx, row in enumerate(instructions, 1):
        for col_idx, val in enumerate(row, 1):
            cell = ws_info.cell(row=row_idx, column=col_idx, value=val)
            if row_idx == 1:
                cell.font = Font(bold=True, size=14)
            elif row_idx == 3:
                cell.font = Font(bold=True)

    # Auto-width on main sheet
    col_widths = [20, 25, 12, 45, 15, 12, 10, 15, 30]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="shakti_target_import_template.xlsx"'
        },
    )


# ── Bulk import from Excel ───────────────────────────────────

@router.post("/import")
async def bulk_import_targets(
    file: UploadFile = File(..., description="Excel (.xlsx) file with targets to import"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_analyst),
) -> dict:
    """
    Bulk import targets from an Excel file.
    Expected columns: username, display_name, platform, profile_url, follower_count,
    is_verified, gender, region, notes.
    Returns import summary with counts.
    """
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an Excel file (.xlsx). Download the template from /targets/import/template.xlsx",
        )

    try:
        from openpyxl import load_workbook
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="openpyxl required on server. Install: pip install openpyxl",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB max
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 5MB)",
        )

    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot read Excel file: {exc}",
        )

    ws = wb.active
    if ws is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active sheet found")

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File appears empty. Expected header row + data rows.",
        )

    # Parse header
    raw_headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    col_map: dict[str, int] = {}
    for i, h in enumerate(raw_headers):
        if h in TEMPLATE_COLUMNS:
            col_map[h] = i

    required = {"username", "platform", "profile_url"}
    missing = required - set(col_map.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
            f"Download the template for correct format.",
        )

    # Load existing username+platform combos for dedup
    existing_q = await session.execute(
        select(TargetAccount.username, TargetAccount.platform)
    )
    existing: set[tuple[str, str]] = {
        (r[0].lower(), r[1].value) for r in existing_q.all()
    }

    data_rows = rows[1:501]  # Max 500 rows
    imported = 0
    skipped = 0
    errors: list[dict] = []

    valid_platforms = {"instagram", "twitter", "facebook", "threads"}

    for row_num, row in enumerate(data_rows, 2):
        try:
            def cell(col_name: str) -> Optional[str]:
                idx = col_map.get(col_name)
                if idx is None or idx >= len(row):
                    return None
                val = row[idx]
                return str(val).strip() if val is not None else None

            username = cell("username")
            platform_str = cell("platform")
            profile_url = cell("profile_url")

            if not username or not platform_str or not profile_url:
                skipped += 1
                errors.append({"row": row_num, "error": "Missing required fields"})
                continue

            username = username.lstrip("@").strip()
            platform_str = platform_str.lower().strip()

            if platform_str not in valid_platforms:
                skipped += 1
                errors.append({"row": row_num, "error": f"Invalid platform: {platform_str}"})
                continue

            platform_enum = PlatformType(platform_str)

            # Dedup check
            key = (username.lower(), platform_str)
            if key in existing:
                skipped += 1
                errors.append({"row": row_num, "error": f"@{username} on {platform_str} already exists"})
                continue

            # Parse optional fields
            display_name = cell("display_name")
            follower_str = cell("follower_count")
            follower_count = None
            if follower_str:
                try:
                    follower_count = int(float(follower_str))
                except (ValueError, TypeError):
                    pass

            is_verified_str = cell("is_verified")
            is_verified = is_verified_str and is_verified_str.lower() in ("yes", "true", "1")

            gender = cell("gender") or "unknown"
            region = cell("region")
            notes = cell("notes")

            target = TargetAccount(
                username=username,
                display_name=display_name,
                platform=platform_enum,
                profile_url=profile_url,
                follower_count=follower_count,
                is_verified=is_verified,
                is_active=True,
                monitoring_enabled=True,
                inferred_region=region,
                notes=notes,
                added_by=current_user.id,
                source=TargetSource.ADMIN_PANEL,
            )
            session.add(target)
            existing.add(key)
            imported += 1

        except Exception as exc:
            skipped += 1
            errors.append({"row": row_num, "error": str(exc)})

    if imported > 0:
        await session.commit()
    else:
        await session.rollback()

    return {
        "status": "completed",
        "total_rows": len(data_rows),
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:20],  # Return first 20 errors only
        "message": f"Successfully imported {imported} targets. {skipped} skipped.",
    }
