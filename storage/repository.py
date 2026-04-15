"""
storage.repository — LeadRepository: the single write path for the pipeline.

All pipeline stages pass data forward as in-memory dataclass objects.
Only LeadRepository touches the database, keeping I/O at the system boundary.

Upsert strategy per table
--------------------------
companies    ON CONFLICT (domain)       DO UPDATE SET name, industry, …, updated_at
sources      ON CONFLICT (content_hash) DO NOTHING  (same article is never re-processed)
pages        ON CONFLICT (url)          DO UPDATE SET content_hash, crawled_at, …
             → if content_hash changed: also clear body_text so parsing re-runs
signals      ON CONFLICT (company, type, page/source)
             DO UPDATE SET confidence = GREATEST(excluded.confidence, signals.confidence)
ai_assessments ON CONFLICT (company_id) DO UPDATE SET all LLM output fields
lead_queue   ON CONFLICT (company_id)  DO UPDATE SET score, tier, status, …

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from config import settings
from utils.logging import get_logger
from .base import AbstractRepository
from .models import Base, Company, Source, Page, Signal, AIAssessment, LeadQueue

logger = get_logger(__name__)


def _get_engine():  # type: ignore[no-untyped-def]
    """
    TODO: Create and return a sqlalchemy.Engine from settings.database.url.

    Pseudocode:
      from sqlalchemy import create_engine
      return create_engine(
          settings.database.url,
          pool_size=settings.database.pool_size,
          echo=settings.database.echo_sql,
      )
    """
    raise NotImplementedError


class LeadRepository(AbstractRepository):
    """
    Idempotent write path for scored and enriched leads.

    Accepts either ScoredLead or EnrichedLead objects (the --skip-ai path
    produces ScoredLead; the full path produces EnrichedLead).  Internally
    it maps both to the lead_queue and ai_assessments tables as appropriate.
    """

    def __init__(self) -> None:
        # TODO: self._engine = _get_engine()
        # TODO: Base.metadata.create_all(self._engine)  # only for SQLite dev
        pass

    def upsert(self, record: object) -> None:
        """
        TODO: Persist a single enriched/scored lead.

        Steps:
        1. Upsert Company          → ON CONFLICT (domain) DO UPDATE
        2. Upsert LeadQueue        → ON CONFLICT (company_id) DO UPDATE
        3. Upsert AIAssessment     → ON CONFLICT (company_id) DO UPDATE  (if EnrichedLead)
        4. Bulk-insert Signals     → ON CONFLICT keep GREATEST confidence
        """
        raise NotImplementedError

    def upsert_many(self, records: list) -> None:
        """
        TODO: Wrap all upserts in a single Session / transaction.

        Pseudocode:
          from sqlalchemy.orm import Session
          with Session(self._engine) as session:
              for record in records:
                  self._upsert_one(session, record)
              session.commit()
          logger.info("storage.committed", count=len(records))
        """
        logger.info("storage.upsert_many.start", count=len(records))
        raise NotImplementedError

    def upsert_page(self, page: Page) -> None:
        """
        TODO: Upsert a crawled page.  If content_hash changed, clear
        body_text so the parsing stage picks it up again.
        """
        raise NotImplementedError

    def upsert_source(self, source: Source) -> None:
        """
        TODO: Insert a source record.  ON CONFLICT (content_hash) DO NOTHING
        — the same article is never processed twice.
        """
        raise NotImplementedError

    def get_qualified_leads(
        self,
        min_score: float | None = None,
        status: str | None = None,
    ) -> list[LeadQueue]:
        """
        TODO: Query lead_queue with optional score and status filters.
        Used by CRM exporters and the outreach sequencer.

        Pseudocode:
          query = select(LeadQueue).join(Company)
          if min_score: query = query.where(LeadQueue.score >= min_score)
          if status:    query = query.where(LeadQueue.status == status)
          return session.scalars(query.order_by(LeadQueue.score.desc())).all()
        """
        raise NotImplementedError

    def get_unparsed_pages(self, limit: int = 100) -> list[Page]:
        """
        TODO: Return pages where body_text IS NULL and status_code = 200.
        Used by the parsing worker to find pending work.
        """
        raise NotImplementedError
