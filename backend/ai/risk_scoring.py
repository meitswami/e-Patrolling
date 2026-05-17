"""Composite risk scoring for evidence and dossier summaries."""

from __future__ import annotations

from typing import Iterable

from database.models import SeverityLevel


_SEVERITY_WEIGHT = {
    SeverityLevel.LOW: 10,
    SeverityLevel.MEDIUM: 25,
    SeverityLevel.HIGH: 50,
    SeverityLevel.CRITICAL: 80,
}


def composite_risk_score(
    *,
    max_risk: int,
    critical_count: int,
    high_count: int,
    platform_count: int,
    evidence_count: int,
) -> int:
    """
    Aggregate risk for a multi-platform accused person (0–100).
    Used in dossier summaries and repeat-offender prioritization hints.
    """
    base = max_risk
    bonus = min(30, critical_count * 8 + high_count * 4)
    spread = min(15, max(0, platform_count - 1) * 5)
    volume = min(10, evidence_count // 3)
    return min(100, base + bonus + spread + volume)


def severity_distribution_score(severities: Iterable[SeverityLevel]) -> dict[str, int]:
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for sev in severities:
        key = sev.value if hasattr(sev, "value") else str(sev)
        if key in counts:
            counts[key] += 1
    return counts
