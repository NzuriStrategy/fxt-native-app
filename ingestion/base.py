"""
ingestion.base — Abstract contract for all ingestion sources.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawCompanyRecord:
    """
    Minimal company record produced by an ingestion source before any
    crawling or enrichment has taken place.

    Fields are intentionally broad — not all sources provide all data.
    Downstream stages tolerate None values and fill gaps where possible.
    """

    # Stable identifier — typically a domain name or registry ID.
    company_id: str

    name: str
    domain: str | None = None
    industry: str | None = None
    employee_count_estimate: int | None = None
    headquarters_city: str | None = None
    headquarters_country: str | None = None

    # Free-form context from the source (headline, job description excerpt, etc.)
    source_snippet: str | None = None
    source_url: str | None = None
    source_name: str | None = None

    ingested_at: datetime = field(default_factory=datetime.utcnow)

    # Arbitrary extra fields — different sources attach different metadata.
    extra: dict = field(default_factory=dict)


class AbstractIngestor(ABC):
    """
    Base class for all ingestion sources.

    Each subclass pulls data from a single external source
    (news API, job board, company registry, etc.) and normalises
    results into RawCompanyRecord objects.

    Implementors should:
    - Handle pagination internally
    - Raise IngestorError on unrecoverable failures
    - Log progress via utils.logging.get_logger(__name__)
    """

    # Human-readable name shown in logs and CLI output.
    source_name: str = "unknown"

    @abstractmethod
    def fetch(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        Pull records from this source.

        Parameters
        ----------
        limit:
            If provided, return at most this many records.
            Useful for smoke-testing without exhausting API quotas.

        Returns
        -------
        list[RawCompanyRecord]
            Normalised company records. May be empty if the source
            has no new data since the last run.
        """
        ...

    def is_available(self) -> bool:
        """
        Return True if the required credentials / config for this source
        are present. The IngestionOrchestrator skips unavailable sources
        instead of crashing.
        """
        return True


class IngestorError(Exception):
    """Raised when an ingestion source fails unrecoverably."""
