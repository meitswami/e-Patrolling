"""Report generation — CSV/Excel export of evidence."""

import csv
import io
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from auth.middleware import get_current_user
from auth.rbac import require_analyst
from configs.settings import settings
from database.connection import get_session
from database.models import AccusedProfile, EvidenceReport, TargetAccount, User

router = APIRouter()


def _rows_from_db(result) -> list[list]:
    rows = [
        [
            "Evidence ID",
            "Platform",
            "Severity",
            "Risk Score",
            "Target",
            "Accused",
            "Comment",
            "Captured At",
        ]
    ]
    for row, target_u, accused_u in result.all():
        rows.append(
            [
                row.evidence_id,
                row.platform.value,
                row.severity_level.value,
                row.risk_score,
                target_u or "",
                accused_u or "",
                (row.comment_text or "")[:500],
                row.capture_timestamp.isoformat() if row.capture_timestamp else "",
            ]
        )
    return rows


@router.get("/evidence/export.csv")
async def export_evidence_csv(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> StreamingResponse:
    """Download evidence as CSV (no extra dependencies)."""
    Target = aliased(TargetAccount)
    Accused = aliased(AccusedProfile)

    result = await session.execute(
        select(
            EvidenceReport,
            Target.username.label("target_username"),
            Accused.username.label("accused_username"),
        )
        .outerjoin(Target, EvidenceReport.target_id == Target.id)
        .outerjoin(Accused, EvidenceReport.accused_id == Accused.id)
        .order_by(EvidenceReport.created_at.desc())
        .limit(5000)
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in _rows_from_db(result):
        writer.writerow(row)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"patrol_evidence_{stamp}.csv"
    content = buffer.getvalue().encode("utf-8-sig")
    settings.EXPORTS_PATH.mkdir(parents=True, exist_ok=True)
    (settings.EXPORTS_PATH / f"{uuid4().hex[:8]}_{filename}").write_bytes(content)

    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/evidence/export.xlsx")
async def export_evidence_excel(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> StreamingResponse:
    """Download evidence as Excel when openpyxl is installed."""
    try:
        from openpyxl import Workbook
    except ImportError:
        return await export_evidence_csv(session, _user)

    Target = aliased(TargetAccount)
    Accused = aliased(AccusedProfile)

    result = await session.execute(
        select(
            EvidenceReport,
            Target.username.label("target_username"),
            Accused.username.label("accused_username"),
        )
        .outerjoin(Target, EvidenceReport.target_id == Target.id)
        .outerjoin(Accused, EvidenceReport.accused_id == Accused.id)
        .order_by(EvidenceReport.created_at.desc())
        .limit(5000)
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Evidence"
    for row in _rows_from_db(result):
        ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"patrol_evidence_{stamp}.xlsx"
    settings.EXPORTS_PATH.mkdir(parents=True, exist_ok=True)
    (settings.EXPORTS_PATH / f"{uuid4().hex[:8]}_{filename}").write_bytes(buffer.getvalue())
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/evidence/export.pdf")
async def export_evidence_pdf(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_analyst),
) -> StreamingResponse:
    """Summary PDF report (requires reportlab)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
    except ImportError:
        return await export_evidence_csv(session, _user)

    Target = aliased(TargetAccount)
    Accused = aliased(AccusedProfile)
    result = await session.execute(
        select(
            EvidenceReport,
            Target.username.label("target_username"),
            Accused.username.label("accused_username"),
        )
        .outerjoin(Target, EvidenceReport.target_id == Target.id)
        .outerjoin(Accused, EvidenceReport.accused_id == Accused.id)
        .order_by(EvidenceReport.created_at.desc())
        .limit(200)
    )

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 2 * cm
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, y, "PATROL Evidence Report")
    y -= 1 * cm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, y, f"Generated {datetime.now(timezone.utc).isoformat()} UTC")
    y -= 1.2 * cm

    for row, target_u, accused_u in result.all():
        if y < 3 * cm:
            pdf.showPage()
            y = height - 2 * cm
            pdf.setFont("Helvetica", 9)
        line = (
            f"{row.evidence_id} | {row.severity_level.value} | "
            f"@{target_u or '?'} <- @{accused_u or '?'} | {(row.comment_text or '')[:60]}"
        )
        pdf.drawString(2 * cm, y, line[:110])
        y -= 0.55 * cm

    pdf.save()
    buffer.seek(0)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"patrol_evidence_{stamp}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/status")
async def reports_status(_user: User = Depends(get_current_user)) -> dict:
    formats = ["csv"]
    try:
        import openpyxl  # noqa: F401

        formats.append("xlsx")
    except ImportError:
        pass
    try:
        import reportlab  # noqa: F401

        formats.append("pdf")
    except ImportError:
        pass
    return {"formats": formats, "max_rows": 5000}
