"""Crawler demo_mode property tests."""

from crawlers.facebook.adapter import FacebookCrawler
from crawlers.threads.adapter import ThreadsCrawler
from services import system_settings as ss


def setup_function():
    ss.invalidate_cache()


def test_facebook_demo_when_no_token_or_credentials(monkeypatch):
    ss._cache["crawler_demo_mode"] = "false"
    monkeypatch.setattr("configs.settings.settings.FACEBOOK_ACCESS_TOKEN", None)
    crawler = FacebookCrawler()
    assert crawler.demo_mode is True


def test_threads_demo_without_instagram(monkeypatch):
    ss._cache["crawler_demo_mode"] = "false"
    crawler = ThreadsCrawler()
    assert crawler.demo_mode is True
