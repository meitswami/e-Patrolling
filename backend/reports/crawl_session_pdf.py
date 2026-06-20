"""PDF export for a single crawl session report."""

import io
from datetime import datetime, timezone
from typing import Any

from utils.duration_format import duration_from_timestamps, format_duration_seconds


def _draw_line(pdf, margin: float, y: float, text: str, *, bold: bool = False, size: int = 9) -> float:
    pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    pdf.drawString(margin, y, (text or "")[:120])
    return y - (size * 0.045 * 72 / 2.54)


def render_crawl_session_pdf(session: dict[str, Any]) -> io.BytesIO:
    """Build a multi-section PDF from crawl session detail JSON."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - 2 * cm

    def new_page_if_needed(min_y: float = 3 * cm) -> None:
        nonlocal y
        if y < min_y:
            pdf.showPage()
            y = height - 2 * cm
            pdf.setFont("Helvetica", 9)

    username = session.get("target_username") or "unknown"
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, f"PATROL Crawl Session Report — @{username}")
    y -= 0.8 * cm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, y, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    y -= 1 * cm

    duration = duration_from_timestamps(
        session.get("started_at"),
        session.get("completed_at"),
        session.get("duration_seconds"),
    )

    summary_lines = [
        ("Target", f"@{username} ({session.get('platform', '?')})"),
        ("Log ID", str(session.get("log_id", ""))),
        ("Status", "OK" if session.get("success") else "Failed"),
        ("Crawl mode", session.get("crawl_mode") or "single"),
        ("Duration", duration),
        ("Started", str(session.get("started_at", ""))[:19]),
        ("Completed", str(session.get("completed_at", ""))[:19] if session.get("completed_at") else "—"),
        ("Comments found", str(session.get("comments_found", 0))),
        ("New comments", str(session.get("comments_new", 0))),
        ("Abusive detected", str(session.get("abusive_detected", 0))),
        ("Critical detected", str(session.get("critical_detected", 0))),
        ("Pages crawled", str(session.get("pages_crawled", 0))),
    ]
    if session.get("error_message"):
        summary_lines.append(("Error", str(session.get("error_message"))[:100]))

    y = _draw_line(pdf, margin, y, "Crawl Summary", bold=True, size=12)
    y -= 0.2 * cm
    for label, value in summary_lines:
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, f"  {label}: {value}")

    specs = session.get("session_data", {}).get("system_specs") or {}
    if specs:
        y -= 0.4 * cm
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, "System Specs (at crawl start)", bold=True, size=12)
        y -= 0.2 * cm
        for key in (
            "hostname", "os", "os_release", "architecture", "processor",
            "cpu_count", "python_version", "ram_total_mb", "disk_total_gb",
        ):
            if key in specs:
                new_page_if_needed()
                y = _draw_line(pdf, margin, y, f"  {key}: {specs[key]}")

    perf = session.get("session_data", {}).get("performance") or {}
    if perf:
        y -= 0.4 * cm
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, "Performance During Crawl", bold=True, size=12)
        y -= 0.2 * cm
        peak = perf.get("peak") or {}
        avg = perf.get("average") or {}
        for metric in ("ram_percent", "cpu_percent", "swap_percent", "disk_percent"):
            label = metric.replace("_percent", "").upper()
            new_page_if_needed()
            y = _draw_line(
                pdf, margin, y,
                f"  {label}: peak {peak.get(metric, 0)}% · avg {avg.get(metric, 0)}%",
            )
        spikes = perf.get("spikes") or []
        y -= 0.2 * cm
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, f"  Resource spikes (≥{perf.get('spike_threshold_percent', 95)}%): {len(spikes)}", bold=True)
        for spike in spikes[:20]:
            new_page_if_needed()
            y = _draw_line(
                pdf, margin, y,
                f"    {spike.get('metric')} {spike.get('value')}% @ {str(spike.get('timestamp', ''))[:19]}",
                size=8,
            )

    activity = session.get("session_data", {}).get("activity_log") or []
    if activity:
        y -= 0.4 * cm
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, f"Live Crawl Activity ({len(activity)} events)", bold=True, size=12)
        y -= 0.2 * cm
        for entry in activity[:80]:
            new_page_if_needed()
            ts = str(entry.get("timestamp", ""))[:19]
            msg = entry.get("message", "")[:90]
            y = _draw_line(pdf, margin, y, f"  [{ts}] {msg}", size=8)
        if len(activity) > 80:
            new_page_if_needed()
            y = _draw_line(pdf, margin, y, f"  … and {len(activity) - 80} more events", size=8)

    evidence = session.get("evidence") or []
    if evidence:
        y -= 0.4 * cm
        new_page_if_needed()
        y = _draw_line(pdf, margin, y, f"Abusive Evidence ({len(evidence)} items)", bold=True, size=12)
        y -= 0.2 * cm
        for ev in evidence[:30]:
            new_page_if_needed()
            line = (
                f"  {ev.get('evidence_id')} | {ev.get('severity')} | "
                f"@{ev.get('accused_username') or '?'} | {(ev.get('comment_preview') or '')[:50]}"
            )
            y = _draw_line(pdf, margin, y, line, size=8)

    pdf.save()
    buffer.seek(0)
    return buffer
