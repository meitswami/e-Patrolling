"""Abuse lexicon file loading."""

from ai.classifier import classify_comment
from ai.keyword_engine import analyze_text
from ai.text_normalize import normalize_for_abuse_detection


def test_lexicon_detects_chinal():
    result = analyze_text("You are a chinal, get lost")
    assert result.is_abusive is True
    assert "sexual_harassment" in result.matched_keywords


def test_lexicon_detects_obfuscated_sex():
    assert normalize_for_abuse_detection("S*X?") == "sex?"
    result = analyze_text("S*X?")
    assert result.is_abusive is True
    assert "sexual_harassment" in result.matched_keywords


def test_lexicon_detects_misspelled_fuck_you():
    assert normalize_for_abuse_detection("Fcuk U") == "fuck u"
    result = analyze_text("Fcuk U")
    assert result.is_abusive is True
    assert result.confidence_score >= 0.88


def test_classifier_flags_english_profanity():
    for text in ("S*X?", "Fcuk U", "f**k you", "you bitch"):
        out = classify_comment(text)
        assert out.is_abusive is True, f"expected abusive for: {text!r}"
