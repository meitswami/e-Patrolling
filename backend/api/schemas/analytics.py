"""Analytics / dashboard schemas."""

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    active_targets: int
    evidence_24h: int
    critical_total: int
    repeat_offenders: int
    total_evidence: int
    live_monitoring: bool = False
