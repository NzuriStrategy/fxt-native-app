"""
storage.repository — LeadRepository: the single write path for the pipeline.

All pipeline stages read from in-memory objects and pass data forward.
Only LeadRepository writes to the database, keeping I/O at the boundary.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from config import settings
from utils.logging import get_logger
from .base import AbstractRepository
from .models import Base, Company, Lead, StoredSignal

logger = get_logger(__name__)


def _get_engine():  # type: ignore[no-untyped-def]
    """
    TODO: Create and return an sqlalchemy.Engine configured from settings.
    """
    raise NotImplementedError


class LeadRepository(AbstractRepository):
    """
    Idempotent write path for enriched leads.

    Each pipeline run generates a unique run_id (UUID) so multiple runs
    can be compared without overwriting previous results.
    """

    def __init__(self) -> None:
        self._run_id = str(uuid.uuid4())
        # TODO: self._engine = _get_engine()
        # TODO: Base.metadata.create_all(self._engine)

    def upsert(self, record: object) -> None:
        """
        TODO: Persist a single EnrichedLead to the database.

        Steps:
        1. Upsert Company record (on conflict update last_updated_at)
        2. Insert Lead row for this run_id
        3. Bulk-insert StoredSignal rows linked to the Lead
        """
        raise NotImplementedError

    def upsert_many(self, records: list) -> None:
        """
        TODO: Wrap all upserts in a single SQLAlchemy session/transaction.

        Pseudocode:
          with Session(self._engine) as session:
              for record in records:
                  self._upsert_one(session, record)
              session.commit()
        """
        logger.info("storage.upsert_many", count=len(records), run_id=self._run_id)
        raise NotImplementedError

    def get_qualified_leads(self, min_score: float | None = None) -> list:
        """
        TODO: Query and return all qualified leads above optional min_score.
        Used by downstream exporters (CRM sync, reporting dashboard).
        """
        raise NotImplementedError
