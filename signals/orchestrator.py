"""
signals.orchestrator — Fans out all detectors across all parsed documents.
"""

from __future__ import annotations

from ingestion.base import RawCompanyRecord
from parsing.base import ParsedDocument
from utils.logging import get_logger
from .base import AbstractSignal, CompanySignalBundle
from .warehouse import (
    WarehouseExpansionSignal,
    DensificationKeywordSignal,
    CapacityConstraintSignal,
)
from .employment import (
    LogisticsHiringSurgeSignal,
    VPSupplyChainHireSignal,
)
from .real_estate import (
    NewLeaseSignedSignal,
    DCConstructionSignal,
)

logger = get_logger(__name__)

# All registered signal detectors — add new ones here
ALL_DETECTORS: list[AbstractSignal] = [
    WarehouseExpansionSignal(),
    DensificationKeywordSignal(),
    CapacityConstraintSignal(),
    LogisticsHiringSurgeSignal(),
    VPSupplyChainHireSignal(),
    NewLeaseSignedSignal(),
    DCConstructionSignal(),
]


class SignalOrchestrator:
    """
    Runs every detector over every document for every company and
    collects results into a CompanySignalBundle per company.
    """

    def __init__(self, detectors: list[AbstractSignal] | None = None) -> None:
        self._detectors = detectors or ALL_DETECTORS

    def run(
        self,
        records: list[RawCompanyRecord],
        documents: list[ParsedDocument],
    ) -> list[CompanySignalBundle]:
        """
        For each company:
        1. Filter documents to those belonging to this company
        2. Run all detectors over each document
        3. Collect results into a CompanySignalBundle

        TODO: Implement the fan-out loop and signal collection.
        """
        # Group documents by company_id for efficient lookup
        docs_by_company: dict[str, list[ParsedDocument]] = {}
        for doc in documents:
            docs_by_company.setdefault(doc.company_id, []).append(doc)

        bundles: list[CompanySignalBundle] = []

        for record in records:
            bundle = CompanySignalBundle(company_id=record.company_id)
            company_docs = docs_by_company.get(record.company_id, [])

            for doc in company_docs:
                for detector in self._detectors:
                    try:
                        results = detector.detect(doc)
                        bundle.signals.extend(results)
                    except Exception as exc:
                        logger.error(
                            "signal.detection_error",
                            company_id=record.company_id,
                            signal=detector.signal_type,
                            error=str(exc),
                        )

            logger.debug(
                "signals.bundle_ready",
                company_id=record.company_id,
                signal_count=len(bundle.signals),
            )
            bundles.append(bundle)

        return bundles
