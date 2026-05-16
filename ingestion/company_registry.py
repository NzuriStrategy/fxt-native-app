"""
ingestion.company_registry — Ingest candidate companies from a CSV file.

Expected CSV columns
--------------------
company_name  : display name of the company (required — rows missing this are skipped)
domain        : website domain or URL (required — normalised to bare hostname)
source        : originating data source tag, e.g. "crm_export", "trade_show"

Any extra columns are preserved in RawCompanyRecord.extra under the key
"extra_fields" so no information is silently dropped.

Deduplication
-------------
Within a single CSV run, domain is used as the dedup key (case-insensitive,
after normalisation).  The first occurrence wins; subsequent rows for the same
domain are counted as ``skipped_duplicate`` and logged at DEBUG level.

Cross-run deduplication is handled at the database layer by the repository
(ON CONFLICT (domain) DO UPDATE).
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from utils.logging import get_logger
from .base import AbstractIngestor, RawCompanyRecord
from .normalizers import normalize_company_name, normalize_domain

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result summary
# ---------------------------------------------------------------------------

@dataclass
class CSVIngestionResult:
    """Counters and error list populated by CompanyRegistryIngestor.fetch()."""
    total_rows: int = 0
    parsed: int = 0
    skipped_invalid: int = 0
    skipped_duplicate: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def acceptance_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.parsed / self.total_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_content_hash(name: str, domain: str, source: str) -> str:
    """SHA-256 of (name, domain, source) — used for idempotent source rows."""
    payload = f"{name.lower()}|{domain}|{source.lower()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Ingestor
# ---------------------------------------------------------------------------

class CompanyRegistryIngestor(AbstractIngestor):
    """
    Reads a structured list of companies from a CSV file and returns them as
    RawCompanyRecord objects ready for crawling and signal detection.
    """

    source_name = "company_registry"

    def __init__(self, csv_path: str | Path | None = None) -> None:
        if csv_path is None:
            from config import settings
            csv_path = settings.ingestion.csv_path or "data/sample_companies.csv"
        self.csv_path = Path(csv_path)
        self._result: CSVIngestionResult | None = None

    # ------------------------------------------------------------------
    # AbstractIngestor interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        return self.csv_path.exists()

    def fetch(self, limit: int | None = None) -> list[RawCompanyRecord]:
        """
        Parse the CSV and return valid, deduplicated RawCompanyRecord objects.

        Parameters
        ----------
        limit:
            Accept at most this many valid records.  Invalid and duplicate rows
            do not count toward the limit.  ``None`` means no limit.

        Side effects
        ------------
        Populates ``self.result`` with parse statistics after every call.
        """
        result = CSVIngestionResult()
        records: list[RawCompanyRecord] = []
        seen_domains: set[str] = set()

        with self.csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)

            for raw_row in reader:
                result.total_rows += 1
                row_num = result.total_rows  # 1-based, header excluded

                # ── Normalise fields ──────────────────────────────────
                raw_name   = raw_row.get("company_name", "")
                raw_domain = raw_row.get("domain", "")
                raw_source = raw_row.get("source", "")

                name   = normalize_company_name(raw_name)
                domain = normalize_domain(raw_domain)

                # ── Validate ──────────────────────────────────────────
                if not name:
                    msg = f"Row {row_num}: missing company_name"
                    result.errors.append(msg)
                    result.skipped_invalid += 1
                    logger.warning("csv.skip.no_name", row=row_num, domain=raw_domain)
                    continue

                if not domain:
                    msg = f"Row {row_num}: invalid or missing domain ({raw_domain!r})"
                    result.errors.append(msg)
                    result.skipped_invalid += 1
                    logger.warning("csv.skip.bad_domain", row=row_num, name=name, raw_domain=raw_domain)
                    continue

                # ── In-file deduplication ─────────────────────────────
                if domain in seen_domains:
                    msg = f"Row {row_num}: duplicate domain {domain!r} (first occurrence kept)"
                    result.errors.append(msg)
                    result.skipped_duplicate += 1
                    logger.debug("csv.skip.duplicate", row=row_num, domain=domain, name=name)
                    continue

                seen_domains.add(domain)

                # ── Build record ──────────────────────────────────────
                extra_fields = {
                    k: v for k, v in raw_row.items()
                    if k not in ("company_name", "domain", "source")
                }
                record = RawCompanyRecord(
                    company_id=domain,  # domain is the stable dedup key
                    name=name,
                    domain=domain,
                    source_name=raw_source or "csv_import",
                    source_snippet=f"CSV row {row_num}: {name} / {domain}",
                    extra={
                        "csv_source": raw_source or "unknown",
                        **extra_fields,
                    },
                )
                records.append(record)
                result.parsed += 1
                logger.debug("csv.accepted", row=row_num, domain=domain, name=name)

                if limit is not None and result.parsed >= limit:
                    logger.info("csv.limit_reached", limit=limit)
                    break

        self._result = result
        logger.info(
            "csv.parse_complete",
            total=result.total_rows,
            parsed=result.parsed,
            skipped_invalid=result.skipped_invalid,
            skipped_duplicate=result.skipped_duplicate,
        )
        return records

    @property
    def result(self) -> CSVIngestionResult | None:
        """The CSVIngestionResult from the most recent fetch() call, or None."""
        return self._result
