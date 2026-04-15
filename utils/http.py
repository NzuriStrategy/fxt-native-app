"""
utils.http — Shared async HTTP client wrapper.

Wraps httpx.AsyncClient with:
- Default headers (User-Agent, Accept)
- Configurable timeout from settings
- Automatic retry on transient errors (5xx, connection reset) via tenacity
- Response size guard (reject responses > MAX_RESPONSE_BYTES)

Import the module-level `client` instance for lightweight callers,
or create a new HttpClient for custom configuration.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from config import settings
from utils.logging import get_logger

logger = get_logger(__name__)

# Reject responses larger than 10 MB to avoid memory exhaustion
MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": settings.crawling.user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class HttpClient:
    """
    Async HTTP client with retry and size limiting.

    Intended to be used as an async context manager:

        async with HttpClient() as client:
            response = await client.get("https://example.com")

    Or via the module-level singleton `default_client`.

    Not yet implemented — this is a structural stub.
    """

    def __init__(
        self,
        timeout: int | None = None,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
    ) -> None:
        self._timeout = timeout or settings.crawling.request_timeout_seconds
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._max_retries = max_retries
        # TODO: self._client = httpx.AsyncClient(...)

    async def get(self, url: str, **kwargs) -> "httpx.Response":  # type: ignore[name-defined]
        """
        TODO: Implement GET with retry (tenacity) and size guard.

        Pseudocode:
          @retry(stop=stop_after_attempt(self._max_retries), wait=wait_exponential(...))
          async def _fetch():
              response = await self._client.get(url, follow_redirects=True, **kwargs)
              if len(response.content) > MAX_RESPONSE_BYTES:
                  raise ResponseTooLargeError(url, len(response.content))
              return response
          return await _fetch()
        """
        raise NotImplementedError

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(self, *args) -> None:
        # TODO: await self._client.aclose()
        pass


class ResponseTooLargeError(Exception):
    """Raised when a response exceeds MAX_RESPONSE_BYTES."""

    def __init__(self, url: str, size: int) -> None:
        super().__init__(f"Response from {url} is {size} bytes (limit {MAX_RESPONSE_BYTES})")
