"""
storage — Persist and query lead intelligence data.

Responsibilities
----------------
- Define SQLAlchemy ORM models (tables: companies, leads, signal_results, crawl_cache)
- Provide a repository layer (LeadRepository) as the single write path for the pipeline
- Expose query helpers for downstream consumers (CRM export, dashboard API, etc.)
- Manage DB migrations via Alembic

The repository is idempotent: upserting the same company record twice
produces a single up-to-date row, not a duplicate.
"""

from .repository import LeadRepository
from .base import AbstractRepository

__all__ = [
    "LeadRepository",
    "AbstractRepository",
]
