"""Tests for DB-backed system settings helpers."""

from services import system_settings as ss


def setup_function():
    ss.invalidate_cache()


def test_crawler_demo_mode_from_cache():
    ss._cache["crawler_demo_mode"] = "false"
    assert ss.get_crawler_demo_mode() is False

    ss._cache["crawler_demo_mode"] = "true"
    assert ss.get_crawler_demo_mode() is True


def test_evidence_screenshot_mode_from_cache():
    ss._cache["evidence_screenshot_mode"] = "playwright"
    assert ss.get_evidence_screenshot_mode() == "playwright"


def test_encrypt_decrypt_roundtrip():
    plain = "test-password-123"
    cipher = ss.encrypt_secret(plain)
    assert cipher != plain
    assert ss.decrypt_secret(cipher) == plain


def test_instagram_credentials_configured():
    ss._cache["instagram_username"] = "patrol_user"
    ss._cache["instagram_password"] = ss.encrypt_secret("secret")
    assert ss.instagram_credentials_configured() is True
    assert ss.get_instagram_username() == "patrol_user"


def test_use_ml_classifier_from_cache():
    ss._cache["use_ml_classifier"] = "true"
    assert ss.get_use_ml_classifier() is True
    ss._cache["use_ml_classifier"] = "false"
    assert ss.get_use_ml_classifier() is False


def test_use_hf_inference_api_from_cache():
    ss._cache["use_hf_inference_api"] = "on"
    assert ss.get_use_hf_inference_api() is True
    ss._cache["use_hf_inference_api"] = "0"
    assert ss.get_use_hf_inference_api() is False
