"""
crawling.web_crawler — HTTP-based crawler using httpx.

Suitable for standard server-rendered HTML pages.
Uses an async connection pool with configurable concurrency limits.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractCrawler, CrawlResult, CrawlTarget

logger = get_logger(__name__)


class WebCrawler(AbstractCrawler):
    """
    Fast, stateless HTTP crawler backed by httpx.AsyncClient.

    Features (planned):
    - Configurable concurrency via asyncio semaphore
    - Automatic retry with exponential back-off (tenacity)
    - robots.txt compliance
    - Response caching to avoid redundant fetches within a run
    """

    def crawl(self, target: CrawlTarget) -> CrawlResult:
        """
        TODO: Implement single-URL async fetch.

        Pseudocode:
          async with httpx.AsyncClient(headers=..., timeout=...) as client:
              response = await client.get(target.url, follow_redirects=True)
              return CrawlResult(
                  company_id=target.company_id,
                  url=str(response.url),
                  status_code=response.status_code,
                  content=response.text,
                  content_type=response.headers.get("content-type", ""),
                  headers=dict(response.headers),
              )
        """
        raise NotImplementedError

    def crawl_many(self, targets: list[CrawlTarget]) -> list[CrawlResult]:
        """
        TODO: Run crawl() for all targets concurrently via asyncio.gather
        with a semaphore limited to settings.crawling.max_concurrent_requests.
        """
        raise NotImplementedError
