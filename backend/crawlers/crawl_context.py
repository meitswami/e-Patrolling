"""Context variable for the active crawl log ID (used by activity broadcast + tracker)."""

from contextvars import ContextVar
from typing import Optional
from uuid import UUID

_crawl_log_id: ContextVar[Optional[UUID]] = ContextVar("crawl_log_id", default=None)


def set_crawl_log_id(log_id: UUID) -> None:
    _crawl_log_id.set(log_id)


def get_crawl_log_id() -> Optional[UUID]:
    return _crawl_log_id.get()


def reset_crawl_log_id() -> None:
    _crawl_log_id.set(None)
