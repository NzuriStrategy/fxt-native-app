"""
storage — Persist and query lead intelligence data.

Responsibilities
----------------
- Define SQLAlchemy ORM models (see models.py; matches storage/schema.sql exactly)
- Provide a repository layer (LeadRepository) as the single write path for the pipeline
- Expose query helpers for downstream consumers (CRM export, dashboard API, etc.)
- Manage DB migrations via Alembic (see alembic/ directory)

Tables: companies, sources, pages, signals, ai_assessments, lead_queue

The repository is idempotent: upserting the same company or lead twice
produces a single up-to-date row, not a duplicate.
"""

from .repository import LeadRepository
from .base import AbstractRepository
from .models import (
    Base,
    Company,
    Source,
    Page,
    Signal,
    AIAssessment,
    LeadQueue,
    SourceType,
    LeadStatus,
    LeadTier,
)

__all__ = [
    "LeadRepository",
    "AbstractRepository",
    "Base",
    "Company",
    "Source",
    "Page",
    "Signal",
    "AIAssessment",
    "LeadQueue",
    "SourceType",
    "LeadStatus",
    "LeadTier",
]
