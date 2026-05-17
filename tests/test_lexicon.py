"""Abuse lexicon file loading."""

from ai.keyword_engine import analyze_text


def test_lexicon_detects_chinal():
    result = analyze_text("You are a chinal, get lost")
    assert result.is_abusive is True
    assert "sexual_harassment" in result.matched_keywords
