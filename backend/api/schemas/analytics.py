"""Analytics / dashboard schemas."""

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    active_targets: int
    evidence_24h: int
    critical_total: int
    repeat_offenders: int
    total_evidence: int
    live_monitoring: bool = False


class SeverityBreakdown(BaseModel):
    LOW: int = 0
    MEDIUM: int = 0
    HIGH: int = 0
    CRITICAL: int = 0


class PlatformBreakdown(BaseModel):
    platform: str
    count: int


class AnalyticsOverview(BaseModel):
    dashboard: DashboardStatsResponse
    by_severity: SeverityBreakdown
    by_platform: list[PlatformBreakdown]
