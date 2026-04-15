"""
signals.base — Core types and abstract contract for signal detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """
    Taxonomy of signals the pipeline looks for.

    Warehouse signals indicate direct capacity or density pressure.
    Employment signals indicate operational scaling.
    Real-estate signals indicate physical footprint changes.
    """

    # Warehouse / density
    WAREHOUSE_EXPANSION_MENTIONED = "warehouse_expansion_mentioned"
    DENSIFICATION_KEYWORD = "densification_keyword"
    SKU_GROWTH_MENTIONED = "sku_growth_mentioned"
    WMS_EVALUATION = "wms_evaluation"
    CAPACITY_CONSTRAINT_MENTIONED = "capacity_constraint_mentioned"

    # Employment
    LOGISTICS_HIRING_SURGE = "logistics_hiring_surge"
    VP_SUPPLY_CHAIN_HIRE = "vp_supply_chain_hire"
    WAREHOUSE_OPS_HIRING = "warehouse_ops_hiring"

    # Real-estate
    NEW_LEASE_SIGNED = "new_lease_signed"
    DC_CONSTRUCTION_MENTIONED = "dc_construction_mentioned"
    THIRD_PARTY_LOGISTICS = "third_party_logistics"


@dataclass
class SignalResult:
    """
    A single signal detected in a document for a specific company.

    confidence is a float in [0.0, 1.0]:
      1.0 = exact keyword match or explicit statement
      0.5 = inferred from context
      0.0 = not detected (results with 0.0 are not appended)

    evidence_snippet is a short excerpt from the source text that
    triggered this detection — used for human review and LLM prompting.
    """

    company_id: str
    signal_type: SignalType
    confidence: float  # [0.0, 1.0]
    source_url: str
    evidence_snippet: str

    detected_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


@dataclass
class CompanySignalBundle:
    """
    All signals detected for a single company across all its documents.
    Passed to the Scorer to produce a ScoredLead.
    """

    company_id: str
    signals: list[SignalResult] = field(default_factory=list)

    def signals_of_type(self, signal_type: SignalType) -> list[SignalResult]:
        return [s for s in self.signals if s.signal_type == signal_type]

    @property
    def max_confidence(self) -> float:
        return max((s.confidence for s in self.signals), default=0.0)


class AbstractSignal(ABC):
    """
    Base class for signal detectors.

    Each detector scans ParsedDocument objects for evidence of a specific
    signal type and returns zero or more SignalResult objects.

    Detectors must be stateless and re-entrant — the orchestrator may run
    them concurrently across documents.
    """

    signal_type: SignalType

    @abstractmethod
    def detect(self, doc: "parsing.base.ParsedDocument") -> list[SignalResult]:  # type: ignore[name-defined]
        """
        Scan `doc` for this signal.

        Returns an empty list if no signal is detected.
        Never raises — catch and log internal errors, return [].
        """
        ...
