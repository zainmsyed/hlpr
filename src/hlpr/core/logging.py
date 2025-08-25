"""Logging utilities for hlpr."""
from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(level: str | int = "INFO") -> None:
    if isinstance(level, str):
        level = level.upper()
    root = logging.getLogger()
    if root.handlers:
        return  # already configured
    logging.basicConfig(level=level, format=LOG_FORMAT)


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or "hlpr")
