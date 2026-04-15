"""
storage.models — SQLAlchemy 2.0 ORM models for the lead intelligence pipeline.

Six tables (matches storage/schema.sql exactly):

  companies       — canonical company master record; domain is the dedup key
  sources         — raw ingestion records (articles, job postings, registry entries)
  pages           — crawled web pages and their parsed body text
  signals         — detected signals linked to exactly one page OR one source
  ai_assessments  — LLM enrichment output; one row per company, updated in place
  lead_queue      — scored, qualified leads; the pipeline's output surface

Enum note
---------
SignalType   is imported from signals.base  (single definition, domain layer owns it)
ConfidenceClass is imported from ai.base    (single definition, AI layer owns it)
SourceType, LeadStatus, LeadTier are storage-specific and defined here.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Import canonical enum definitions from domain layers to avoid duplication.
# Dependency direction: storage → signals, storage → ai (both are one-way).
from signals.base import SignalType
from ai.base import ConfidenceClass


# ---------------------------------------------------------------------------
# Storage-specific Python enums (no equivalent in domain layers)
# ---------------------------------------------------------------------------

class SourceType(str, enum.Enum):
    NEWS_FEED = "news_feed"
    JOB_BOARD = "job_board"
    COMPANY_REGISTRY = "company_registry"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    DISQUALIFIED = "disqualified"
    CONVERTED = "converted"
    SNOOZED = "snoozed"


class LeadTier(str, enum.Enum):
    HOT = "HOT"
    WARM = "WARM"
    COOL = "COOL"
    COLD = "COLD"


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# companies
# ---------------------------------------------------------------------------

class Company(Base):
    """
    Canonical company record.  All FK references in other tables point to
    companies.id (bigserial surrogate key).

    domain is the stable business-level dedup key.  When two ingestion
    sources mention the same domain they map to the same Company row.
    domain is nullable because a company may be discovered from a news
    mention before its website is known.
    """

    __tablename__ = "companies"
    __table_args__ = (
        Index("idx_companies_industry", "industry"),
        Index("idx_companies_hq_country", "hq_country"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(Text)
    employee_count: Mapped[Optional[int]] = mapped_column(BigInteger)
    hq_city: Mapped[Optional[str]] = mapped_column(Text)
    hq_country: Mapped[Optional[str]] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sources: Mapped[list[Source]] = relationship(
        "Source", back_populates="company", cascade="all, delete-orphan"
    )
    pages: Mapped[list[Page]] = relationship(
        "Page", back_populates="company", cascade="all, delete-orphan"
    )
    signals: Mapped[list[Signal]] = relationship(
        "Signal", back_populates="company", cascade="all, delete-orphan"
    )
    ai_assessment: Mapped[Optional[AIAssessment]] = relationship(
        "AIAssessment", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )
    lead_queue_entry: Mapped[Optional[LeadQueue]] = relationship(
        "LeadQueue", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------

class Source(Base):
    """
    One row per ingestion event (news article, job posting, registry entry).

    content_hash (SHA-256 of normalised source content) is the primary
    dedup key.  The same article will never be stored twice regardless of
    which pipeline run fetched it.
    """

    __tablename__ = "sources"
    __table_args__ = (
        Index("idx_sources_company_id", "company_id"),
        Index("idx_sources_source_type", "source_type"),
        Index("idx_sources_published_at", "published_at"),
        Index("idx_sources_ingested_at", "ingested_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="source_type", native_enum=True), nullable=False
    )
    # Friendly provider label: 'newsapi.org', 'linkedin', 'apollo.io', …
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)

    # SHA-256 of the normalised source content — unique constraint prevents re-ingest
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # snippet: key excerpt passed to signal detectors (avoids loading raw_content every time)
    snippet: Mapped[Optional[str]] = mapped_column(Text)
    # raw_content: full text retained for re-processing when detection logic changes
    raw_content: Mapped[Optional[str]] = mapped_column(Text)

    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    company: Mapped[Company] = relationship("Company", back_populates="sources")
    signals: Mapped[list[Signal]] = relationship(
        "Signal", back_populates="source", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

class Page(Base):
    """
    One row per crawled URL.  Upserted on every re-crawl via ON CONFLICT (url).

    Lifecycle:
      1. Crawled  → content_hash set, body_text NULL, status_code recorded
      2. Parsed   → body_text populated by the parsing stage
      3. Re-crawl → if content_hash unchanged: only crawled_at updated;
                    body_text and linked signals are left untouched
    """

    __tablename__ = "pages"
    __table_args__ = (
        Index("idx_pages_company_id", "company_id"),
        Index("idx_pages_content_hash", "content_hash"),
        Index("idx_pages_page_type", "page_type"),
        Index("idx_pages_crawled_at", "crawled_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # SHA-256 of raw HTTP response body.
    # Unchanged hash on re-crawl → skip re-parse and re-signal.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(Text)

    # Classifier label set during parsing: 'careers', 'press_room', 'about', …
    page_type: Mapped[Optional[str]] = mapped_column(Text)

    # Clean body text from the parsing stage.  NULL = not yet parsed.
    body_text: Mapped[Optional[str]] = mapped_column(Text)

    js_rendered: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # created_at: first crawl (immutable).  crawled_at: updated on every re-crawl.
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    crawled_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    @property
    def is_parsed(self) -> bool:
        return self.body_text is not None

    @property
    def content_changed(self, previous_hash: str) -> bool:
        return self.content_hash != previous_hash

    company: Mapped[Company] = relationship("Company", back_populates="pages")
    signals: Mapped[list[Signal]] = relationship(
        "Signal", back_populates="page", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# signals
# ---------------------------------------------------------------------------

class Signal(Base):
    """
    One detected signal per (company, signal_type, origin).

    Origin is XOR: a signal comes from EITHER a crawled Page OR an ingestion
    Source — never both, never neither.  The chk_signals_xor_origin constraint
    enforces this at the database level.

    Upsert strategy: ON CONFLICT (company, signal_type, page/source)
    DO UPDATE SET confidence = GREATEST(excluded.confidence, signals.confidence)
    — so we always keep the highest observed confidence for a given signal.
    """

    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint(
            "(page_id IS NULL) != (source_id IS NULL)",
            name="chk_signals_xor_origin",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="chk_signals_confidence_range",
        ),
        Index("idx_signals_company_id", "company_id"),
        Index("idx_signals_signal_type", "signal_type"),
        Index("idx_signals_confidence", "confidence"),
        Index("idx_signals_detected_at", "detected_at"),
        # Composite used by the scoring query
        Index("idx_signals_company_detected", "company_id", "detected_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    # Exactly one of page_id / source_id is set (XOR)
    page_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("pages.id", ondelete="CASCADE"), nullable=True
    )
    source_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sources.id", ondelete="CASCADE"), nullable=True
    )
    signal_type: Mapped[SignalType] = mapped_column(
        # native_enum=True uses the Postgres signal_type_enum type defined in schema.sql
        SAEnum(SignalType, name="signal_type_enum", native_enum=True), nullable=False
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    company: Mapped[Company] = relationship("Company", back_populates="signals")
    page: Mapped[Optional[Page]] = relationship("Page", back_populates="signals")
    source: Mapped[Optional[Source]] = relationship("Source", back_populates="signals")


# ---------------------------------------------------------------------------
# ai_assessments
# ---------------------------------------------------------------------------

class AIAssessment(Base):
    """
    LLM-generated company assessment.  One row per company; updated in place
    each time the company is re-assessed (UNIQUE on company_id).

    score_at_assessment records the pipeline score when the LLM was called.
    If the score has since changed by more than a threshold, the assessment
    can be flagged as stale and refreshed.

    expires_at: NULL means the assessment does not automatically expire.
    The pipeline can set a TTL (e.g. 30 days) to force periodic refreshes.
    """

    __tablename__ = "ai_assessments"
    __table_args__ = (
        Index("idx_ai_assessments_confidence", "confidence_class"),
        Index("idx_ai_assessments_assessed", "assessed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_used: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_class: Mapped[ConfidenceClass] = mapped_column(
        SAEnum(ConfidenceClass, name="confidence_class", native_enum=True), nullable=False
    )
    narrative_summary: Mapped[str] = mapped_column(Text, nullable=False)
    outreach_angle: Mapped[str] = mapped_column(Text, nullable=False)
    score_at_assessment: Mapped[float] = mapped_column(nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    assessed_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    @property
    def is_stale(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(tz=timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    company: Mapped[Company] = relationship("Company", back_populates="ai_assessment")
    lead_queue_entries: Mapped[list[LeadQueue]] = relationship(
        "LeadQueue", back_populates="assessment"
    )


# ---------------------------------------------------------------------------
# lead_queue
# ---------------------------------------------------------------------------

class LeadQueue(Base):
    """
    Pipeline output surface.  One row per qualified company; updated in place
    as scores and CRM statuses change (UNIQUE on company_id).

    top_signals (TEXT[]) is intentionally denormalized: it stores the top 3
    signal_type values by weight so list-view queries never need to JOIN
    back to the signals table.

    snoozed_until is only meaningful when status = 'snoozed'.
    assessment_id is NULL when --skip-ai is used or AI has not yet run.
    """

    __tablename__ = "lead_queue"
    __table_args__ = (
        CheckConstraint("score >= 0.0 AND score <= 100.0", name="chk_lead_queue_score_range"),
        Index("idx_lead_queue_score", "score"),
        Index("idx_lead_queue_tier", "tier"),
        Index("idx_lead_queue_status", "status"),
        Index("idx_lead_queue_last_scored", "last_scored_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    assessment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("ai_assessments.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float] = mapped_column(nullable=False)
    tier: Mapped[LeadTier] = mapped_column(
        SAEnum(LeadTier, name="lead_tier", native_enum=True), nullable=False
    )
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status", native_enum=True),
        nullable=False,
        server_default="new",
    )
    signal_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    # Denormalized top-3 signal types for fast list-view display
    top_signals: Mapped[list] = mapped_column(
        ARRAY(Text()), nullable=False, server_default="{}"
    )
    qualified_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    last_scored_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    @property
    def is_active(self) -> bool:
        return self.status not in (LeadStatus.DISQUALIFIED, LeadStatus.CONVERTED)

    @property
    def is_snoozed(self) -> bool:
        if self.snoozed_until is None:
            return False
        return datetime.now(tz=timezone.utc) < self.snoozed_until.replace(tzinfo=timezone.utc)

    company: Mapped[Company] = relationship("Company", back_populates="lead_queue_entry")
    assessment: Mapped[Optional[AIAssessment]] = relationship(
        "AIAssessment", back_populates="lead_queue_entries"
    )
