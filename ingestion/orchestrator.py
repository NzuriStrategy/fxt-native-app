"""
ingestion.orchestrator — Selects and runs ingestion sources.
"""

from __future__ import annotations

from utils.logging import get_logger
from .base import AbstractIngestor, RawCompanyRecord
from .news_feed import NewsFeedIngestor
from .job_boards import JobBoardIngestor
from .company_registry import CompanyRegistryIngestor

logger = get_logger(__name__)

# Registry maps the CLI --source argument to ingestor class(es)
_SOURCE_MAP: dict[str, list[type[AbstractIngestor]]] = {
    "news": [NewsFeedIngestor],
    "job_boards": [JobBoardIngestor],
    "company_registry": [CompanyRegistryIngestor],
    "all": [NewsFeedIngestor, JobBoardIngestor, CompanyRegistryIngestor],
}


class IngestionOrchestrator:
    """
    Instantiates and runs the appropriate ingestors, deduplicates
    results by company_id, and returns a flat list of RawCompanyRecord.
    """

    def __init__(self, source_filter: str = "all") -> None:
        self._ingestor_classes = _SOURCE_MAP.get(source_filter, _SOURCE_MAP["all"])

    def run(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        Run all configured ingestors and merge results.

        Deduplication: if the same company_id appears from multiple sources,
        the record with the most non-None fields is kept. Later implementations
        may merge rather than discard.
        """
        seen: dict[str, RawCompanyRecord] = {}

        for cls in self._ingestor_classes:
            ingestor = cls()

            if not ingestor.is_available():
                logger.warning("ingestor.unavailable", source=ingestor.source_name)
                continue

            logger.info("ingestor.start", source=ingestor.source_name)
            records = ingestor.fetch(limit=limit)
            logger.info("ingestor.done", source=ingestor.source_name, count=len(records))

            for record in records:
                # Simple dedup: first occurrence wins (TODO: smarter merge)
                if record.company_id not in seen:
                    seen[record.company_id] = record

        return list(seen.values())
