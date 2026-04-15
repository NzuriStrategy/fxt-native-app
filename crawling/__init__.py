"""
crawling — Fetch web content for companies that need deeper enrichment.

Responsibilities
----------------
- Accept a list of RawCompanyRecord objects and resolve URLs to crawl
- Manage concurrency (httpx async pool + Playwright for JS-rendered pages)
- Respect robots.txt, honour rate limits, retry transiently failed requests
- Return CrawlResult objects containing raw HTML, HTTP metadata, and timestamps

Two crawlers are provided:
  WebCrawler    — async HTTP crawls via httpx (fast, stateless pages)
  SitemapCrawler — discovers page URLs via sitemap.xml before crawling

The CrawlingOrchestrator selects the appropriate crawler per URL.
"""

from .base import AbstractCrawler, CrawlResult
from .orchestrator import CrawlingOrchestrator

__all__ = [
    "AbstractCrawler",
    "CrawlResult",
    "CrawlingOrchestrator",
]
