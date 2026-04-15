"""
utils.rate_limiter — Token-bucket rate limiter for external API calls.

Used to enforce per-domain and per-API-key request rate limits so the
pipeline doesn't get blocked or incur overage charges.

Usage:
    limiter = RateLimiter(calls_per_second=2.0)
    async with limiter:
        response = await http_client.get(url)

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimiter:
    """
    Async token-bucket rate limiter.

    Parameters
    ----------
    calls_per_second:
        Maximum number of calls allowed per second.
    burst:
        Maximum number of tokens that can accumulate (burst capacity).
        Defaults to calls_per_second (no burst).
    """

    calls_per_second: float
    burst: float = field(default=0.0)

    _tokens: float = field(default=0.0, init=False)
    _last_refill: float = field(default_factory=time.monotonic, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def __post_init__(self) -> None:
        if self.burst == 0.0:
            self.burst = self.calls_per_second
        self._tokens = self.burst

    async def __aenter__(self) -> "RateLimiter":
        """
        TODO: Acquire a token, blocking until one is available.

        Pseudocode:
          async with self._lock:
              self._refill()
              while self._tokens < 1.0:
                  wait_time = (1.0 - self._tokens) / self.calls_per_second
                  await asyncio.sleep(wait_time)
                  self._refill()
              self._tokens -= 1.0
        """
        raise NotImplementedError

    async def __aexit__(self, *args) -> None:
        pass

    def _refill(self) -> None:
        """
        TODO: Add tokens proportional to elapsed time since last refill.

        Pseudocode:
          now = time.monotonic()
          elapsed = now - self._last_refill
          self._tokens = min(self.burst, self._tokens + elapsed * self.calls_per_second)
          self._last_refill = now
        """
        raise NotImplementedError


# Pre-configured limiters for common external services
NEWS_API_LIMITER = RateLimiter(calls_per_second=1.0)   # newsapi.org free tier
ANTHROPIC_LIMITER = RateLimiter(calls_per_second=5.0)  # conservative default
WEB_CRAWL_LIMITER = RateLimiter(calls_per_second=2.0)  # per-domain politeness
