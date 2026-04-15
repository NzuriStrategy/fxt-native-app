"""
crawling.base — Abstract contract for all web crawlers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CrawlResult:
    """
    Raw output of a single URL crawl.

    Contains the full HTML (or document bytes), HTTP metadata, and
    provenance information so downstream parsers and signal detectors
    can trace every text fragment back to its source.
    """

    company_id: str
    url: str
    status_code: int

    # Raw page content (HTML string or base64 bytes for binary docs)
    content: str
    content_type: str  # e.g. "text/html", "application/pdf"

    # HTTP response headers (useful for caching and content-type negotiation)
    headers: dict[str, str] = field(default_factory=dict)

    crawled_at: datetime = field(default_factory=datetime.utcnow)

    # True if the page was rendered via Playwright (JS-heavy SPA pages)
    js_rendered: bool = False

    # HTTP error message if status_code >= 400
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass
class CrawlTarget:
    """
    Describes a URL the crawler should visit, with hints about how to crawl it.
    Produced by the CrawlingOrchestrator from a RawCompanyRecord.
    """

    company_id: str
    url: str

    # When True, the orchestrator uses Playwright instead of plain httpx
    requires_js: bool = False

    # Page priority — higher priority targets are crawled first
    priority: int = 0

    # Human-readable label for logging (e.g. "careers_page", "press_room")
    label: str = "unknown"


class AbstractCrawler(ABC):
    """
    Base class for URL crawlers.

    Subclasses implement the actual HTTP (or browser) fetch.
    The orchestrator selects the right crawler per target.
    """

    @abstractmethod
    def crawl(self, target: CrawlTarget) -> CrawlResult:
        """
        Fetch the URL described by `target` and return a CrawlResult.

        Should not raise on HTTP errors — encode them in CrawlResult.status_code
        and CrawlResult.error instead so the pipeline can continue.
        """
        ...

    @abstractmethod
    def crawl_many(self, targets: list[CrawlTarget]) -> list[CrawlResult]:
        """
        Crawl multiple targets, ideally with concurrency.

        Default implementations may call crawl() in a thread pool;
        async subclasses may use asyncio.gather.
        """
        ...


class CrawlerError(Exception):
    """Raised when a crawl fails unrecoverably (e.g. network unavailable)."""
