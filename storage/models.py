"""
storage.models — SQLAlchemy ORM table definitions.

Four tables:
  companies      — deduplicated company master records
  leads          — scored + enriched leads (one row per company per run cycle)
  signal_results — individual signals that contributed to a lead score
  crawl_cache    — cached page content to avoid re-fetching within a run window
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    """
    Canonical company record. Ingestion sources upsert into this table;
    all other tables reference it by company_id.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    employee_count_estimate: Mapped[int | None] = mapped_column(Integer)
    headquarters_city: Mapped[str | None] = mapped_column(String(255))
    headquarters_country: Mapped[str | None] = mapped_column(String(10))

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    leads: Mapped[list["Lead"]] = relationship("Lead", back_populates="company")


class Lead(Base):
    """
    Scored and enriched lead record.

    One row per (company_id, pipeline_run_id) — multiple pipeline runs
    produce versioned lead records so score trends can be tracked over time.
    """

    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("company_id", "pipeline_run_id", name="uq_lead_company_run"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("companies.company_id"), nullable=False, index=True
    )
    pipeline_run_id: Mapped[str] = mapped_column(String(36), nullable=False)  # UUID

    score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(10))  # HOT / WARM / COOL / COLD
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI enrichment outputs
    narrative_summary: Mapped[str | None] = mapped_column(Text)
    confidence_class: Mapped[str | None] = mapped_column(String(10))  # HIGH/MEDIUM/LOW
    outreach_angle: Mapped[str | None] = mapped_column(Text)

    # Cost tracking
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)

    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime)

    company: Mapped["Company"] = relationship("Company", back_populates="leads")
    signals: Mapped[list["StoredSignal"]] = relationship("StoredSignal", back_populates="lead")


class StoredSignal(Base):
    """
    Individual signal that contributed to a Lead's score.
    Stored for audit, model tuning, and human review.
    """

    __tablename__ = "signal_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_snippet: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(2048))
    detected_at: Mapped[datetime] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="signals")


class CrawlCache(Base):
    """
    Cached page content. Prevents re-fetching the same URL within
    a configurable TTL window (default: 24 hours).
    """

    __tablename__ = "crawl_cache"
    __table_args__ = (
        UniqueConstraint("url", name="uq_crawl_cache_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    company_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(100))
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
