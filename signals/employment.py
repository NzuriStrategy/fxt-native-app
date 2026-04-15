"""
signals.employment — Detectors for logistics and warehousing hiring signals.

Rationale: companies scaling warehouse operations typically hire ahead of
infrastructure investment. A surge in logistics/ops postings is a leading
indicator of densification need.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from parsing.base import ParsedDocument
from utils.logging import get_logger
from .base import AbstractSignal, SignalResult, SignalType

logger = get_logger(__name__)

LOGISTICS_HIRE_TITLES: list[str] = [
    "warehouse manager",
    "distribution center manager",
    "supply chain analyst",
    "inventory control",
    "logistics coordinator",
    "fulfillment operations",
]

VP_TITLES: list[str] = [
    "VP supply chain",
    "Vice President supply chain",
    "VP logistics",
    "VP operations",
    "Chief Supply Chain Officer",
    "SVP logistics",
]


class LogisticsHiringSurgeSignal(AbstractSignal):
    """
    Detects a cluster of logistics/warehouse job postings from a single company.
    A surge (>3 open roles) within a short window suggests operational scaling.
    """

    signal_type = SignalType.LOGISTICS_HIRING_SURGE

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Count matching job titles in doc.body_text.
        Return a signal with confidence proportional to posting count.
        """
        raise NotImplementedError


class VPSupplyChainHireSignal(AbstractSignal):
    """
    Detects VP or C-suite supply chain hiring — a strong signal that
    leadership is re-evaluating operations strategy.
    """

    signal_type = SignalType.VP_SUPPLY_CHAIN_HIRE

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan for VP_TITLES with high confidence (0.9) on exact match.
        """
        raise NotImplementedError
