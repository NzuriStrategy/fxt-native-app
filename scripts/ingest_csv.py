"""
scripts/ingest_csv.py — Ingest company records from a CSV file into Postgres.

This script runs the full CSV ingestion path end-to-end:
  1. Parse and normalise the CSV (CompanyRegistryIngestor)
  2. Upsert companies into the ``companies`` table
  3. Record provenance rows in the ``sources`` table
  4. Print a structured summary

Usage
-----
::

    # Full run
    poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv

    # Parse and validate only — no database writes
    poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv --dry-run

    # Smoke-test with the first 5 valid records
    poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv --limit 5

    # Verbose mode — shows every accepted/skipped row
    poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv --log-level DEBUG

Prerequisites
-------------
* PostgreSQL running and ``DATABASE__URL`` set in ``.env`` (or environment).
* Schema applied: ``psql -d <db> -f storage/schema.sql``
  (or tables created automatically via ``Base.metadata.create_all`` for dev).

The script is safe to re-run: upserts are idempotent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as `python scripts/ingest_csv.py` from the project root
# without needing an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.company_registry import CompanyRegistryIngestor, CSVIngestionResult
from storage.repository import CompanyUpsertResult, LeadRepository
from utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

# ── Formatting helpers ────────────────────────────────────────────────────────

_DIVIDER = "─" * 52


def _header(title: str) -> str:
    return f"\n── {title} {_DIVIDER[len(title) + 4:]}"


def _print_parse_summary(csv_path: str, result: CSVIngestionResult) -> None:
    print(_header("CSV Parse Results"))
    print(f"  File              : {csv_path}")
    print(f"  Total rows        : {result.total_rows}")
    print(f"  Valid records     : {result.parsed}")
    print(f"  Skipped (invalid) : {result.skipped_invalid}")
    print(f"  Skipped (in-file) : {result.skipped_duplicate}")
    if result.skipped_invalid or result.skipped_duplicate:
        print(f"\n  Issues ({len(result.errors)}):")
        for err in result.errors:
            print(f"    ✗  {err}")


def _print_db_summary(result: CompanyUpsertResult) -> None:
    print(_header("Database Results"))
    print(f"  Inserted (new)    : {result.inserted}")
    print(f"  Updated (existed) : {result.updated}")
    print(f"  Skipped (no domain): {result.skipped}")
    print(f"  Total upserted    : {result.inserted + result.updated}")


# ── Argument parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest_csv",
        description=(
            "Ingest company records from a CSV file into the "
            "lead intelligence Postgres database."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv
  poetry run python scripts/ingest_csv.py --csv accounts.csv --dry-run
  poetry run python scripts/ingest_csv.py --csv accounts.csv --limit 10
        """,
    )
    parser.add_argument(
        "--csv",
        required=True,
        metavar="FILE",
        help="Path to the CSV file.  Required columns: company_name, domain, source.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the CSV but skip all database writes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Accept at most N valid records (invalid/duplicate rows do not count).",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO).",
    )
    return parser


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:  # noqa: C901
    parser = _build_parser()
    args = parser.parse_args()

    # Apply log level before any imports that log at module load time
    import os
    os.environ.setdefault("LOG_LEVEL", args.log_level)
    configure_logging()

    logger.info(
        "ingest_csv.start",
        csv=args.csv,
        dry_run=args.dry_run,
        limit=args.limit,
    )

    # ── Step 1: Parse the CSV ─────────────────────────────────────────
    ingestor = CompanyRegistryIngestor(csv_path=args.csv)

    if not ingestor.is_available():
        print(f"\nError: CSV file not found: {args.csv}", file=sys.stderr)
        logger.error("ingest_csv.file_not_found", path=args.csv)
        return 1

    try:
        records = ingestor.fetch(limit=args.limit)
    except Exception as exc:
        print(f"\nError reading CSV: {exc}", file=sys.stderr)
        logger.error("ingest_csv.parse_failed", error=str(exc))
        return 1

    parse_result = ingestor.result
    assert parse_result is not None  # always set after fetch()

    _print_parse_summary(args.csv, parse_result)

    if not records:
        print("\nNo valid records to process.")
        return 0

    # ── Step 2: Write to database ─────────────────────────────────────
    if args.dry_run:
        print(f"\nDry-run mode — skipping database writes.")
        print(f"Would attempt to upsert {parse_result.parsed} record(s).")
        logger.info("ingest_csv.dry_run_complete", would_upsert=parse_result.parsed)
        return 0

    try:
        repo = LeadRepository()
        db_result = repo.upsert_companies(records)
    except Exception as exc:
        print(f"\nDatabase error: {exc}", file=sys.stderr)
        logger.error("ingest_csv.db_failed", error=str(exc))
        return 1

    _print_db_summary(db_result)

    logger.info(
        "ingest_csv.complete",
        inserted=db_result.inserted,
        updated=db_result.updated,
        skipped_db=db_result.skipped,
        skipped_invalid=parse_result.skipped_invalid,
        skipped_duplicate=parse_result.skipped_duplicate,
    )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
