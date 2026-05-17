"""PDF export for multi-platform accused dossier."""

from __future__ import annotations

import io
from typing import Any


def render_dossier_pdf(dossier: dict[str, Any]) -> io.BytesIO:
    """Build a multi-page PDF from dossier JSON (requires reportlab)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - margin

    def new_page() -> None:
        nonlocal y
        pdf.showPage()
        y = height - margin
        pdf.setFont("Helvetica", 9)

    def line(text: str, size: int = 9, bold: bool = False) -> None:
        nonlocal y
        if y < 2.5 * cm:
            new_page()
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(margin, y, (text or "")[:120])
        y -= 0.5 * cm

    username = dossier.get("username", "unknown")
    summary = dossier.get("summary", {})

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(margin, y, f"PATROL Accused Dossier — @{username}")
    y -= 0.8 * cm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Generated {dossier.get('generated_at', '')}")
    y -= 1 * cm

    line(f"Platforms: {', '.join(dossier.get('platforms', []))}", bold=True)
    line(f"Total evidence: {summary.get('total_evidence', 0)}")
    line(f"Targets affected: {summary.get('targets_affected_count', 0)}")
    line(f"Max risk score: {summary.get('max_risk_score', 0)}")
    sev = summary.get("severity_breakdown", {})
    line(
        f"Severity — CRITICAL:{sev.get('CRITICAL',0)} HIGH:{sev.get('HIGH',0)} "
        f"MEDIUM:{sev.get('MEDIUM',0)} LOW:{sev.get('LOW',0)}"
    )
    y -= 0.3 * cm

    line("Platform profiles", bold=True, size=11)
    for prof in dossier.get("profiles", []):
        line(
            f"  [{prof.get('platform')}] @{prof.get('username')} — "
            f"{prof.get('total_incidents', 0)} incidents, risk max {prof.get('max_risk_score', 0)}"
        )
        if prof.get("profile_url"):
            line(f"    {prof.get('profile_url')}", size=8)
    y -= 0.3 * cm

    line("Evidence records", bold=True, size=11)
    for ev in dossier.get("evidence", [])[:100]:
        line(
            f"{ev.get('evidence_id')} | {ev.get('platform')} | {ev.get('severity')} | "
            f"risk {ev.get('risk_score')} | target @{ev.get('target_username') or '?'}"
        )
        preview = (ev.get("comment_text") or "")[:90].replace("\n", " ")
        if preview:
            line(f"    \"{preview}\"", size=8)
        if ev.get("post_url"):
            line(f"    {ev.get('post_url')}", size=7)

    pdf.save()
    buffer.seek(0)
    return buffer
