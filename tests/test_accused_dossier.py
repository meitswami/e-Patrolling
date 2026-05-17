"""Accused dossier aggregation and risk scoring."""

from ai.risk_scoring import composite_risk_score


def test_composite_risk_score_caps_at_100():
    score = composite_risk_score(
        max_risk=90,
        critical_count=5,
        high_count=3,
        platform_count=4,
        evidence_count=20,
    )
    assert score == 100


def test_composite_risk_score_minimal():
    score = composite_risk_score(
        max_risk=40,
        critical_count=0,
        high_count=0,
        platform_count=1,
        evidence_count=1,
    )
    assert score == 40
