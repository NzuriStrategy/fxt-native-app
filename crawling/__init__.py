"""
crawling — Fetch web content for companies that need deeper enrichment.

Responsibilities
----------------
- Accept a list of RawCompanyRecord objects and resolve URLs to crawl
- Manage concurrency (httpx async pool + Playwright for JS-rendered pages)
- Respect robots.txt, honour rate limits, retry transiently failed requests
- Return CrawlResult objects containing raw HTML, HTTP metadata, and timestamps

One crawler is currently provided:
  WebCrawler — async HTTP crawls via httpx (fast, stateless pages)

SitemapCrawler (sitemap.xml discovery) will be added once WebCrawler
is implemented and validated against real targets.

The CrawlingOrchestrator builds URL targets from company domains and
dispatches them to the crawler.
"""

from .base import AbstractCrawler, CrawlResult
from .orchestrator import CrawlingOrchestrator

__all__ = [
    "AbstractCrawler",
    "CrawlResult",
    "CrawlingOrchestrator",
]
