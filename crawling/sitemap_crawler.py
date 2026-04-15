"""
crawling.sitemap_crawler — Discovers and crawls URLs via sitemap.xml.

Useful for finding press release and news pages on corporate sites
that don't follow a predictable URL structure.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractCrawler, CrawlResult, CrawlTarget

logger = get_logger(__name__)


class SitemapCrawler(AbstractCrawler):
    """
    Fetches sitemap.xml, extracts relevant page URLs (filtered by keyword
    patterns like "press", "news", "warehouse"), then delegates individual
    page fetches to WebCrawler.

    Features (planned):
    - Recursive sitemap index support
    - URL filtering by keyword patterns
    - Prioritisation by <lastmod> date
    """

    def crawl(self, target: CrawlTarget) -> CrawlResult:
        """
        TODO: Fetch and parse sitemap.xml at the target URL.
        Return a synthetic CrawlResult containing discovered URLs in `content`.
        """
        raise NotImplementedError

    def crawl_many(self, targets: list[CrawlTarget]) -> list[CrawlResult]:
        """
        TODO: Process multiple sitemap targets and aggregate discovered pages.
        """
        raise NotImplementedError
