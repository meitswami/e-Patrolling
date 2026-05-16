"""Map confidence scores to severity levels and risk scores."""

from database.models import SeverityLevel


def severity_from_score(confidence: float) -> SeverityLevel:
    if confidence >= 0.9:
        return SeverityLevel.CRITICAL
    if confidence >= 0.75:
        return SeverityLevel.HIGH
    if confidence >= 0.55:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW


def risk_score_from_confidence(confidence: float) -> int:
    return min(100, max(0, int(confidence * 100)))
