"""
crawling.orchestrator — Builds crawl targets from company records and dispatches crawlers.
"""

from __future__ import annotations

from ingestion.base import RawCompanyRecord
from utils.logging import get_logger
from .base import AbstractCrawler, CrawlResult, CrawlTarget
from .web_crawler import WebCrawler
from .sitemap_crawler import SitemapCrawler

logger = get_logger(__name__)

# URL path patterns to crawl per company domain
TARGET_PATHS: list[tuple[str, str, bool]] = [
    # (path_suffix, label, requires_js)
    ("/careers", "careers_page", False),
    ("/jobs", "careers_page", False),
    ("/press", "press_room", False),
    ("/news", "news_room", False),
    ("/investors", "investor_relations", False),
    ("/about", "about_page", False),
    ("/sitemap.xml", "sitemap", False),
]


class CrawlingOrchestrator:
    """
    For each RawCompanyRecord:
    1. Resolves a list of CrawlTarget URLs to visit
    2. Selects the appropriate crawler (WebCrawler vs SitemapCrawler)
    3. Runs crawls with concurrency control
    4. Returns all CrawlResult objects for downstream parsing
    """

    def __init__(self) -> None:
        self._web_crawler: AbstractCrawler = WebCrawler()
        self._sitemap_crawler: AbstractCrawler = SitemapCrawler()

    def run(self, records: list[RawCompanyRecord]) -> list[CrawlResult]:
        """
        Build targets from records and crawl them.

        TODO: Implement target resolution, concurrency, and result collection.
        """
        targets = self._build_targets(records)
        logger.info("crawling.targets_built", count=len(targets))

        results: list[CrawlResult] = []
        # TODO: dispatch targets to appropriate crawlers concurrently
        return results

    def _build_targets(self, records: list[RawCompanyRecord]) -> list[CrawlTarget]:
        """
        For each company with a known domain, generate a CrawlTarget per
        path in TARGET_PATHS.

        TODO: Implement URL construction and validation.
        """
        targets: list[CrawlTarget] = []
        for record in records:
            if not record.domain:
                continue
            for path, label, requires_js in TARGET_PATHS:
                targets.append(
                    CrawlTarget(
                        company_id=record.company_id,
                        url=f"https://{record.domain}{path}",
                        requires_js=requires_js,
                        label=label,
                    )
                )
        return targets
