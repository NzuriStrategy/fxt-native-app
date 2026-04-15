"""
main.py — Lead Intelligence Pipeline Orchestrator

Entry point for the pipeline. Coordinates all stages in sequence:

  1. Ingestion   — pull raw company/signal data from external sources
  2. Crawling    — fetch web pages for companies that need enrichment
  3. Parsing     — extract structured content from raw HTML / documents
  4. Signals     — compute domain-specific signals per company
  5. Scoring     — aggregate signals into a composite lead score
  6. AI          — LLM-based classification and natural-language enrichment
  7. Storage     — persist scored leads; mark disqualified companies

Run:
    poetry run python main.py [--source news] [--limit 100] [--dry-run]
    # or after `poetry install`:
    poetry run pipeline
"""

from __future__ import annotations

import argparse
import sys

from config import settings
from ingestion import IngestionOrchestrator
from crawling import CrawlingOrchestrator
from parsing import ParsingOrchestrator
from signals import SignalOrchestrator
from scoring import Scorer
from ai import AIEnrichmentOrchestrator
from storage import LeadRepository
from utils.logging import get_logger

logger = get_logger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FXT Lead Intelligence Pipeline — identifies companies facing "
                    "warehouse densification constraints."
    )
    parser.add_argument(
        "--source",
        choices=["news", "job_boards", "company_registry", "all"],
        default="all",
        help="Which ingestion source(s) to run (default: all).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of companies processed in this run (useful for testing).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full pipeline but skip writing results to storage.",
    )
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="Skip the crawling stage (use already-cached pages).",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip the AI enrichment stage (saves API costs during development).",
    )
    return parser


def run_pipeline(args: argparse.Namespace) -> int:
    """
    Orchestrates the full pipeline end-to-end.

    Returns an exit code: 0 = success, non-zero = failure.

    Data flows through stages as plain Python objects (Pydantic models) defined in
    storage.models. No stage writes directly to the database — only the final
    storage stage does, making each stage independently testable.
    """
    logger.info("pipeline.start", env=settings.env, source=args.source, dry_run=args.dry_run)

    # ------------------------------------------------------------------
    # Stage 1: Ingestion
    # Pull raw company records and early signals from external sources.
    # Output: list[RawCompanyRecord]
    # ------------------------------------------------------------------
    logger.info("stage.ingestion.start")
    ingestor = IngestionOrchestrator(source_filter=args.source)
    raw_records = ingestor.run(limit=args.limit)
    logger.info("stage.ingestion.done", count=len(raw_records))

    # ------------------------------------------------------------------
    # Stage 2: Crawling
    # For each company, fetch relevant web pages (careers page, press releases,
    # investor relations, news mentions) to gather raw HTML content.
    # Output: list[CrawlResult]
    # ------------------------------------------------------------------
    if args.skip_crawl:
        logger.info("stage.crawling.skipped")
        crawl_results = []
    else:
        logger.info("stage.crawling.start")
        crawler = CrawlingOrchestrator()
        crawl_results = crawler.run(raw_records)
        logger.info("stage.crawling.done", count=len(crawl_results))

    # ------------------------------------------------------------------
    # Stage 3: Parsing
    # Extract structured text, metadata, and candidate signal fragments
    # from raw HTML and documents.
    # Output: list[ParsedDocument]
    # ------------------------------------------------------------------
    logger.info("stage.parsing.start")
    parser = ParsingOrchestrator()
    parsed_docs = parser.run(crawl_results)
    logger.info("stage.parsing.done", count=len(parsed_docs))

    # ------------------------------------------------------------------
    # Stage 4: Signal Detection
    # Run each signal detector over parsed documents.
    # Signals are domain-specific heuristics (warehouse, employment, real-estate).
    # Output: list[CompanySignalBundle]  (one bundle per company)
    # ------------------------------------------------------------------
    logger.info("stage.signals.start")
    signal_orchestrator = SignalOrchestrator()
    signal_bundles = signal_orchestrator.run(raw_records, parsed_docs)
    logger.info("stage.signals.done", bundles=len(signal_bundles))

    # ------------------------------------------------------------------
    # Stage 5: Scoring
    # Aggregate signals into a 0–100 composite score.
    # Companies above settings.scoring.lead_threshold are promoted to leads.
    # Output: list[ScoredLead]
    # ------------------------------------------------------------------
    logger.info("stage.scoring.start")
    scorer = Scorer(threshold=settings.scoring.lead_threshold)
    scored_leads = scorer.score_all(signal_bundles)
    qualified = [l for l in scored_leads if l.is_qualified]
    logger.info("stage.scoring.done", total=len(scored_leads), qualified=len(qualified))

    # ------------------------------------------------------------------
    # Stage 6: AI Enrichment
    # Send qualified leads to the LLM for:
    #   - Narrative summary of why this company is a fit
    #   - Confidence classification
    #   - Recommended outreach angle
    # Output: list[EnrichedLead]
    # ------------------------------------------------------------------
    if args.skip_ai:
        logger.info("stage.ai.skipped")
        enriched_leads = qualified  # type: ignore[assignment]
    else:
        logger.info("stage.ai.start")
        enricher = AIEnrichmentOrchestrator()
        enriched_leads = enricher.run(qualified)
        logger.info("stage.ai.done", count=len(enriched_leads))

    # ------------------------------------------------------------------
    # Stage 7: Storage
    # Upsert enriched leads into the database.
    # Idempotent: re-running the pipeline for the same company updates,
    # not duplicates, existing records.
    # ------------------------------------------------------------------
    if args.dry_run:
        logger.info("stage.storage.skipped", reason="dry-run")
    else:
        logger.info("stage.storage.start")
        repo = LeadRepository()
        repo.upsert_many(enriched_leads)
        logger.info("stage.storage.done", persisted=len(enriched_leads))

    logger.info("pipeline.complete", leads_produced=len(enriched_leads))
    return 0


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    sys.exit(run_pipeline(args))


if __name__ == "__main__":
    main()
