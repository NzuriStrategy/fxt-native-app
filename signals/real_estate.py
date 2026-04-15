"""
signals.real_estate — Detectors for warehouse real-estate activity signals.

Companies signing new leases or announcing DC construction are at a decision
point where densification solutions can be positioned as alternatives or
complements to physical expansion.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from parsing.base import ParsedDocument
from utils.logging import get_logger
from .base import AbstractSignal, SignalResult, SignalType

logger = get_logger(__name__)

LEASE_KEYWORDS: list[str] = [
    "signed a lease",
    "new lease",
    "leased",
    "sq ft",
    "square feet",
    "industrial space",
    "logistics park",
]

CONSTRUCTION_KEYWORDS: list[str] = [
    "broke ground",
    "groundbreaking",
    "under construction",
    "build-to-suit",
    "speculative warehouse",
    "new distribution facility",
]


class NewLeaseSignedSignal(AbstractSignal):
    """
    Detects news of a company signing a warehouse/industrial lease.
    Implies upcoming space planning activity.
    """

    signal_type = SignalType.NEW_LEASE_SIGNED

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan for LEASE_KEYWORDS and extract size (sq ft) as context.
        """
        raise NotImplementedError


class DCConstructionSignal(AbstractSignal):
    """
    Detects mentions of new DC construction — typically the longest-lead
    signal (18–36 months out), useful for early pipeline seeding.
    """

    signal_type = SignalType.DC_CONSTRUCTION_MENTIONED

    def detect(self, doc: ParsedDocument) -> list[SignalResult]:
        """
        TODO: Scan for CONSTRUCTION_KEYWORDS.
        """
        raise NotImplementedError
