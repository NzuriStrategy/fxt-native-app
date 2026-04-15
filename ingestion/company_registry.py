"""
ingestion.company_registry — Seed the pipeline from a structured company list.

Use cases
---------
- Import a static CSV / Airtable export of target accounts
- Pull from Clearbit, Apollo, or similar B2B databases
- Process a CRM export (Salesforce, HubSpot) of existing prospects

This source is typically used to top-up the pipeline with pre-qualified
accounts rather than discovering net-new companies.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractIngestor, RawCompanyRecord

logger = get_logger(__name__)


class CompanyRegistryIngestor(AbstractIngestor):
    """
    Reads a structured list of companies from a configured registry
    (CSV file, database table, or API) and returns them as RawCompanyRecord
    objects ready for crawling and signal detection.
    """

    source_name = "company_registry"

    def fetch(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        TODO: Implement CSV/database/API reads and field mapping.

        Pseudocode:
          rows = registry_source.read(limit=limit)
          return [map_to_raw_record(row) for row in rows]
        """
        raise NotImplementedError
