"""Structured logger factory used across the backend."""

import logging

from configs.settings import settings


def get_logger(name: str) -> logging.Logger:
    """Return a module logger; logging is configured once via logging_config."""
    return logging.getLogger(name)


def configure_root_if_needed() -> None:
    """Ensure root logger has a handler when modules import before main."""
    root = logging.getLogger()
    if not root.handlers:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        )
