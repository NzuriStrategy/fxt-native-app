"""
ingestion.job_boards — Ingest companies via logistics/warehouse job postings.

Rationale
---------
Companies actively hiring for roles like "Director of Warehouse Operations",
"Supply Chain Analyst", or "VP, Fulfilment" are often mid-transformation —
evaluating new storage tech, WMS systems, or space optimisation solutions.

Data sources (planned)
----------------------
- LinkedIn Jobs API (or scraping via Playwright)
- Indeed RSS feeds
- Greenhouse / Lever public job boards

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractIngestor, RawCompanyRecord

logger = get_logger(__name__)


# Job titles that indicate warehouse densification pressure
TARGET_JOB_TITLES: list[str] = [
    "warehouse operations",
    "supply chain",
    "inventory management",
    "distribution center",
    "fulfillment",
    "logistics director",
    "VP supply chain",
    "head of warehousing",
]


class JobBoardIngestor(AbstractIngestor):
    """
    Scans job boards for warehouse/logistics roles and uses the hiring
    company as the raw lead.
    """

    source_name = "job_boards"

    def fetch(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        TODO: Implement job board crawls, title matching, and company
        extraction.

        Pseudocode:
          postings = job_api.search(titles=TARGET_JOB_TITLES, ...)
          companies = deduplicate(postings, key="company_name")
          return [to_raw_record(c) for c in companies]
        """
        raise NotImplementedError
