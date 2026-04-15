"""
signals — Domain-specific detectors for warehouse densification indicators.

Responsibilities
----------------
- Define the vocabulary of signals the pipeline looks for
- Run each detector over ParsedDocument objects and produce SignalResult objects
- Each SignalResult carries: signal_type, confidence (0.0–1.0), evidence snippet,
  and source URL

Three signal families are implemented:
  WarehouseSignal   — keywords, expansions, capacity mentions, SKU growth
  EmploymentSignal  — logistics/ops hiring surges, VP Supply Chain job postings
  RealEstateSignal  — new lease signings, warehouse construction mentions

The SignalOrchestrator fans out all detectors across all documents and groups
results into a CompanySignalBundle (one per company).
"""

from .base import AbstractSignal, SignalResult, CompanySignalBundle
from .orchestrator import SignalOrchestrator

__all__ = [
    "AbstractSignal",
    "SignalResult",
    "CompanySignalBundle",
    "SignalOrchestrator",
]
