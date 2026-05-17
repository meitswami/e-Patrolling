"""Keyword classifier smoke tests."""

from ai.keyword_engine import analyze_text


def test_detects_hindi_abuse():
    result = analyze_text("Tu bahar aa kabhi, sabak sikhaunga")
    assert result.is_abusive is True
    assert result.confidence_score >= 0.65


def test_benign_comment():
    result = analyze_text("Nice photo, great work!")
    assert result.is_abusive is False


def test_empty_text():
    result = analyze_text("  ")
    assert result.is_abusive is False
