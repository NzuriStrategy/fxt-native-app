"""
ingestion — Pull raw company and signal data from external sources.

Responsibilities
----------------
- Connect to third-party APIs (news feeds, job boards, company registries)
- Normalise responses into RawCompanyRecord objects (defined in storage.models)
- Handle pagination, rate limiting, and auth transparently
- Emit structured logs for every record fetched

Implementations of AbstractIngestor are registered here and selected by the
IngestionOrchestrator based on the `source_filter` argument passed from main.py.
"""

from .base import AbstractIngestor, RawCompanyRecord
from .orchestrator import IngestionOrchestrator

__all__ = [
    "AbstractIngestor",
    "RawCompanyRecord",
    "IngestionOrchestrator",
]
