"""
scoring — Aggregate signals into a composite lead score.

Responsibilities
----------------
- Accept a CompanySignalBundle and produce a ScoredLead (0–100 score)
- Apply configurable weights per signal type (see weights.py)
- Apply decay for stale signals (signals older than N days lose weight)
- Expose a threshold check: ScoredLead.is_qualified

The Scorer is deterministic and has no external dependencies —
unit-testable without any mocks.
"""

from .scorer import Scorer
from .base import ScoredLead

__all__ = [
    "Scorer",
    "ScoredLead",
]
