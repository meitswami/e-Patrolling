"""Format crawl duration as DD D HHh MMm SSs."""

def format_duration_seconds(total_seconds: float | None) -> str:
    """Format seconds as '00 D 03H 42M 13S'."""
    if total_seconds is None or total_seconds < 0:
        return "00 D 00H 00M 00S"
    secs = int(round(total_seconds))
    days = secs // 86400
    hours = (secs % 86400) // 3600
    minutes = (secs % 3600) // 60
    seconds = secs % 60
    return (
        f"{days:02d} D {hours:02d}H {minutes:02d}M {seconds:02d}S"
    )


def duration_from_timestamps(
    started_at: str | None,
    completed_at: str | None,
    duration_seconds: float | None = None,
) -> str:
    """Prefer stored duration_seconds, else compute from timestamps."""
    if duration_seconds is not None and duration_seconds >= 0:
        return format_duration_seconds(duration_seconds)
    if started_at and completed_at:
        from datetime import datetime

        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            delta = (end - start).total_seconds()
            if delta >= 0:
                return format_duration_seconds(delta)
        except (TypeError, ValueError):
            pass
    return "00 D 00H 00M 00S"
