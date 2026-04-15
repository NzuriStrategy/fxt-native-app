"""
utils.logging — Structured logging setup using structlog + Rich.

All pipeline modules obtain a logger via:
    from utils.logging import get_logger
    logger = get_logger(__name__)

Log events are emitted as structured key-value records (JSON in production,
colourised human-readable text in development) so they can be parsed by
log aggregation systems (Datadog, CloudWatch, etc.).

Configuration is driven by settings.log_level.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache

import structlog
from config import settings


def configure_logging() -> None:
    """
    Set up structlog with appropriate renderer for the current environment.

    Call this once at application startup (main.py does this automatically).
    Subsequent calls are idempotent.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.env == "development":
        # Human-readable colourised output via Rich
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Machine-parseable JSON for production log aggregators
        renderer = structlog.processors.JSONRenderer()  # type: ignore[assignment]

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so SQLAlchemy, httpx, etc. respect the level
    logging.basicConfig(level=log_level, stream=sys.stdout, format="%(message)s")


@lru_cache(maxsize=None)
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a module-level bound logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("event.name", key="value")
    """
    configure_logging()
    return structlog.get_logger(name)
