"""Crawl stop signal for graceful crawl-all termination."""

from task_queue.scheduler import (
    clear_crawl_stop,
    is_crawl_stop_requested,
    request_crawl_stop,
)


def test_crawl_stop_request_and_clear():
    clear_crawl_stop()
    assert is_crawl_stop_requested() is False
    request_crawl_stop()
    assert is_crawl_stop_requested() is True
    clear_crawl_stop()
    assert is_crawl_stop_requested() is False
