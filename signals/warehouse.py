"""
signals.warehouse — Detectors for direct warehouse densification signals.

These are the highest-weight signals in the scoring model because they
indicate a company is actively thinking about storage capacity.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from parsing.base import ParsedDocument
from utils.logging import get_logger
from .base import AbstractSignal, SignalResult, SignalType

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Keyword lists — to be refined with domain expert input
# ---------------------------------------------------------------------------

EXPANSION_KEYWORDS: list[str] = [
    "warehouse expansion",
    "new distribution center",
    "new DC",
    "additional warehouse",
    "fulfillment center expansion",
    "opened a new facility",
]

DENSIFICATION_KEYWORDS: list[str] = [
    "densification",
    "high-density storage",
    "vertical storage",
    "mezzanine",
    "narrow aisle",
    "very narrow aisle",
    "VNA",
    "automated storage",
    "ASRS",
    "goods-to-person",
]

CAPACITY_CONSTRAINT_KEYWORDS: list[str] = [
    "running out of space",
    "capacity constraints",
    "storage constraints",
    "limited warehouse space",
    "over capacity",
    "inventory overflow",
    "offsite storage",
]


class WarehouseExpansionSignal(AbstractSignal):
    """
    Detects explicit mentions of warehouse or DC expansion.
    Indicates a company is actively growing its footprint.
    """

    signal_type = SignalType.WAREHOUSE_EXPANSION_MENTIONED

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan doc.body_text and doc.keyword_hits for EXPANSION_KEYWORDS.
        Return a SignalResult per match with the matched excerpt as evidence_snippet.
        """
        raise NotImplementedError


class DensificationKeywordSignal(AbstractSignal):
    """
    Detects explicit mentions of storage densification technologies or concepts.
    Highest-confidence signal — these are industry-specific terms.
    """

    signal_type = SignalType.DENSIFICATION_KEYWORD

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan for DENSIFICATION_KEYWORDS with surrounding context extraction.
        """
        raise NotImplementedError


class CapacityConstraintSignal(AbstractSignal):
    """
    Detects language suggesting the company is hitting storage limits.
    Often appears in earnings calls, press releases, or operations blogs.
    """

    signal_type = SignalType.CAPACITY_CONSTRAINT_MENTIONED

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan for CAPACITY_CONSTRAINT_KEYWORDS.
        """
        raise NotImplementedError
