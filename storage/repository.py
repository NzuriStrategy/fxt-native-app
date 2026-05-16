"""
storage.repository — LeadRepository: the single write path for the pipeline.

All pipeline stages pass data forward as in-memory dataclass objects.
Only LeadRepository touches the database, keeping I/O at the system boundary.

Upsert strategy per table
--------------------------
companies     ON CONFLICT (domain)        DO UPDATE name, updated_at
sources       ON CONFLICT (content_hash)  DO NOTHING  (idempotent re-runs)
pages         ON CONFLICT (url)           DO UPDATE content_hash, crawled_at
signals       ON CONFLICT (company+type+page/source)
              DO UPDATE SET confidence = GREATEST(excluded, existing)
ai_assessments ON CONFLICT (company_id)  DO UPDATE all LLM fields
lead_queue    ON CONFLICT (company_id)   DO UPDATE score, tier, status, …

Database compatibility
----------------------
``upsert_companies`` uses ``sqlalchemy.dialects.postgresql.insert`` and
requires PostgreSQL.  SQLite is supported for the default settings URL but
only for stages that do not call this method.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from config import settings
from utils.logging import get_logger
from .base import AbstractRepository
from .models import Base, Company, Source, SourceType

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Engine — module-level singleton, created once per process
# ---------------------------------------------------------------------------

_engine: Engine | None = None


def _get_engine() -> Engine:
    """
    Return (and cache) a SQLAlchemy Engine configured from settings.

    pool_size is passed only for PostgreSQL; SQLite uses the default
    StaticPool and does not accept that argument.
    """
    global _engine
    if _engine is not None:
        return _engine

    url = settings.database.url
    kwargs: dict = {"echo": settings.database.echo_sql}

    if not url.startswith("sqlite"):
        kwargs["pool_size"] = settings.database.pool_size
        kwargs["pool_pre_ping"] = True  # drop stale connections automatically

    _engine = create_engine(url, **kwargs)
    logger.debug("db.engine_created", url=_redact_url(url))
    return _engine


def _redact_url(url: str) -> str:
    """Replace password in a DB URL with *** for safe logging."""
    import re
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)


# ---------------------------------------------------------------------------
# Result type for upsert_companies
# ---------------------------------------------------------------------------

@dataclass
class CompanyUpsertResult:
    """Counts returned by ``LeadRepository.upsert_companies()``."""
    inserted: int = 0   # domains that did not exist in the DB before this call
    updated: int = 0    # domains that already existed (name / metadata refreshed)
    skipped: int = 0    # records without a domain (cannot be keyed)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class LeadRepository(AbstractRepository):
    """
    Idempotent write path for pipeline outputs.

    ``upsert_companies`` is the only fully implemented method today —
    it covers the CSV ingestion path.  The remaining methods are stubs
    that will be implemented as each pipeline stage is built out.
    """

    def __init__(self) -> None:
        self._engine = _get_engine()
        # Create tables that don't yet exist.  Safe to call repeatedly
        # (checkfirst=True).  In production, use Alembic migrations instead.
        Base.metadata.create_all(self._engine, checkfirst=True)

    # ------------------------------------------------------------------
    # CSV ingestion path — fully implemented
    # ------------------------------------------------------------------

    def upsert_companies(
        self,
        records: list,  # list[RawCompanyRecord] — typed loosely to avoid circular import
    ) -> CompanyUpsertResult:
        """
        Upsert a batch of ``RawCompanyRecord`` objects into the ``companies``
        and ``sources`` tables.

        Strategy
        --------
        * ``companies``: ``ON CONFLICT (domain) DO UPDATE`` — always refreshes
          ``name`` and ``updated_at`` so the record stays current.
        * ``sources``: ``ON CONFLICT (content_hash) DO NOTHING`` — re-running
          the same CSV never inserts duplicate provenance rows.

        Returns
        -------
        CompanyUpsertResult
            Counts of inserted, updated, and skipped records.

        Notes
        -----
        Records without a ``domain`` are skipped with a WARNING log.
        This method requires PostgreSQL; it uses ``pg_insert`` which is
        dialect-specific.
        """
        result = CompanyUpsertResult()

        if not records:
            return result

        # Separate records with and without a domain
        keyed   = [r for r in records if r.domain]
        nokey   = [r for r in records if not r.domain]

        for r in nokey:
            logger.warning("upsert.skip.no_domain", company=r.name)
            result.skipped += 1

        if not keyed:
            return result

        domains = [r.domain for r in keyed]

        with Session(self._engine) as session:
            # ── Pre-fetch which domains already exist ───────────────────
            # Used after the upsert to classify rows as inserted vs updated.
            existing_domains: set[str] = {
                row[0]
                for row in session.execute(
                    select(Company.domain).where(Company.domain.in_(domains))
                ).fetchall()
            }

            # ── Upsert companies ────────────────────────────────────────
            for record in keyed:
                company_db_id = self._upsert_company(session, record)

                if record.domain in existing_domains:
                    result.updated += 1
                    logger.info(
                        "company.updated",
                        domain=record.domain,
                        name=record.name,
                    )
                else:
                    result.inserted += 1
                    logger.info(
                        "company.inserted",
                        domain=record.domain,
                        name=record.name,
                    )

                # ── Record ingestion provenance ─────────────────────────
                self._upsert_source_record(session, record, company_db_id)

            session.commit()

        logger.info(
            "upsert_companies.complete",
            inserted=result.inserted,
            updated=result.updated,
            skipped=result.skipped,
        )
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upsert_company(self, session: Session, record) -> int:
        """
        INSERT … ON CONFLICT (domain) DO UPDATE … RETURNING id.

        Always updates ``name`` and ``updated_at`` on conflict so the
        record stays current even when the same domain is ingested again.
        Returns the database PK of the upserted row.
        """
        stmt = pg_insert(Company).values(
            domain=record.domain,
            name=record.name,
            extra=record.extra or {},
        )
        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["domain"],
                set_={
                    "name": stmt.excluded.name,
                    "extra": stmt.excluded.extra,
                    "updated_at": func.now(),
                },
            )
            .returning(Company.id)
        )
        company_db_id: int = session.scalar(stmt)  # type: ignore[assignment]
        return company_db_id

    def _upsert_source_record(
        self,
        session: Session,
        record,
        company_db_id: int,
    ) -> None:
        """
        INSERT a Source row to record that this company came from a CSV.

        ``ON CONFLICT (content_hash) DO NOTHING`` — idempotent.  Re-running
        ingestion on the same CSV never creates duplicate source rows.

        The content_hash is derived from (name, domain, csv_source) so that
        the same physical company imported from two *different* CSV sources
        creates two distinct source rows (useful for attribution).
        """
        from ingestion.company_registry import compute_content_hash

        csv_source = record.extra.get("csv_source", "unknown")
        content_hash = compute_content_hash(record.name, record.domain, csv_source)

        stmt = pg_insert(Source).values(
            company_id=company_db_id,
            source_type=SourceType.COMPANY_REGISTRY,
            source_name=record.source_name or "csv_import",
            content_hash=content_hash,
            snippet=record.source_snippet,
            raw_content=None,   # no raw content for CSV rows
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["content_hash"])
        session.execute(stmt)
        logger.debug(
            "source.recorded",
            company_id=company_db_id,
            csv_source=csv_source,
            content_hash=content_hash[:12] + "…",
        )

    # ------------------------------------------------------------------
    # Pipeline stubs — implemented as stages are built out
    # ------------------------------------------------------------------

    def upsert(self, record: object) -> None:
        """
        TODO: Persist a single EnrichedLead.

        Steps:
        1. Upsert Company          → ON CONFLICT (domain) DO UPDATE
        2. Upsert LeadQueue        → ON CONFLICT (company_id) DO UPDATE
        3. Upsert AIAssessment     → ON CONFLICT (company_id) DO UPDATE
        4. Bulk-insert Signals     → ON CONFLICT keep GREATEST confidence
        """
        raise NotImplementedError

    def upsert_many(self, records: list) -> None:
        """
        TODO: Wrap all upserts in a single Session / transaction.

        Pseudocode:
          with Session(self._engine) as session:
              for record in records:
                  self._upsert_one(session, record)
              session.commit()
        """
        logger.info("storage.upsert_many.start", count=len(records))
        raise NotImplementedError

    def upsert_page(self, page) -> None:
        """
        TODO: Upsert a crawled page.  If content_hash changed, clear
        body_text so the parsing stage picks it up again.
        """
        raise NotImplementedError

    def get_qualified_leads(
        self,
        min_score: float | None = None,
        status: str | None = None,
    ) -> list:
        """
        TODO: Query lead_queue with optional score and status filters.
        """
        raise NotImplementedError

    def get_unparsed_pages(self, limit: int = 100) -> list:
        """
        TODO: Return pages where body_text IS NULL and status_code = 200.
        """
        raise NotImplementedError
