"""
ingestion.news_feed — Ingest company signals from news APIs.

Target signals
--------------
- Companies announcing warehouse expansions, new DCs, or 3PL partnerships
- Retailers reporting inventory overhang or SKU rationalisation
- Supply chain disruption coverage naming specific companies

Data sources (planned)
----------------------
- newsapi.org  (primary)
- GDELT        (large-scale, free)
- RSS feeds    (trade publications: DC Velocity, Supply Chain Dive, etc.)

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from config import settings
from utils.logging import get_logger
from .base import AbstractIngestor, RawCompanyRecord

logger = get_logger(__name__)


class NewsFeedIngestor(AbstractIngestor):
    """
    Pulls articles matching warehouse/logistics keywords from news APIs,
    extracts mentioned company names, and produces RawCompanyRecord stubs.
    """

    source_name = "news_feed"

    # Keywords used to filter articles before company extraction
    QUERY_KEYWORDS: list[str] = [
        "warehouse expansion",
        "distribution center",
        "densification",
        "warehouse capacity",
        "inventory storage",
        "fulfillment center",
        "3PL",
    ]

    def is_available(self) -> bool:
        return settings.ingestion.news_api_key is not None

    def fetch(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        TODO: Implement news API calls, article parsing, and NER-based
        company extraction.

        Pseudocode:
          articles = newsapi.get_everything(q=QUERY_KEYWORDS, ...)
          companies = ner_extract(articles)
          return [to_raw_record(c) for c in companies]
        """
        raise NotImplementedError
