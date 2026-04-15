"""
scoring.base — Core types for the scoring stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from signals.base import CompanySignalBundle, SignalResult


@dataclass
class ScoredLead:
    """
    A company with a computed composite lead score and the signals that
    drove it.

    score is in [0.0, 100.0].
    is_qualified is True when score >= the configured threshold.
    """

    company_id: str
    score: float  # [0.0, 100.0]
    threshold: float

    # Signals that contributed to the score, ordered by contribution (desc)
    contributing_signals: list[SignalResult] = field(default_factory=list)

    # Per-signal-type breakdown for transparency
    score_breakdown: dict[str, float] = field(default_factory=dict)

    source_bundle: CompanySignalBundle | None = None
    scored_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_qualified(self) -> bool:
        return self.score >= self.threshold

    @property
    def tier(self) -> str:
        """Human-readable tier label for quick triage."""
        if self.score >= 80:
            return "HOT"
        if self.score >= 60:
            return "WARM"
        if self.score >= 40:
            return "COOL"
        return "COLD"
