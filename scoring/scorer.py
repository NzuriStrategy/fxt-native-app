"""
scoring.scorer — Aggregates signal bundles into composite lead scores.

The scoring algorithm:
1. For each signal in the bundle, compute: weight × confidence × decay_factor
2. Sum contributions per signal type (cap per type to avoid double-counting)
3. Normalise the total against the maximum possible score
4. Scale to [0, 100]

The Scorer is fully deterministic and has no I/O — unit-testable without mocks.

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from signals.base import CompanySignalBundle
from utils.logging import get_logger
from .base import ScoredLead
from .weights import SIGNAL_WEIGHTS, SIGNAL_STALENESS_DAYS, DECAY_FACTOR

logger = get_logger(__name__)


class Scorer:
    """
    Converts a CompanySignalBundle into a ScoredLead.

    Parameters
    ----------
    threshold:
        Minimum score (0–100) to qualify a company as a lead.
        Defaults to settings.scoring.lead_threshold.
    """

    def __init__(self, threshold: float = 60.0) -> None:
        self._threshold = threshold

    def score(self, bundle: CompanySignalBundle) -> ScoredLead:
        """
        Compute the composite score for a single company.

        TODO: Implement weighted, decayed signal aggregation.

        Pseudocode:
          raw = sum(
              SIGNAL_WEIGHTS[s.signal_type] * s.confidence * decay(s.detected_at)
              for s in bundle.signals
          )
          normalised = min(raw / max_possible_raw * 100, 100.0)
          return ScoredLead(
              company_id=bundle.company_id,
              score=normalised,
              threshold=self._threshold,
              contributing_signals=sorted(bundle.signals, ...),
              source_bundle=bundle,
          )
        """
        raise NotImplementedError

    def score_all(self, bundles: list[CompanySignalBundle]) -> list[ScoredLead]:
        """
        Score all bundles and return results sorted by score descending.
        """
        results = [self.score(b) for b in bundles]
        return sorted(results, key=lambda l: l.score, reverse=True)

    def _decay_factor(self, signal_age_days: int) -> float:
        """
        Return 1.0 for fresh signals, DECAY_FACTOR for stale ones.

        TODO: Implement linear or exponential decay over SIGNAL_STALENESS_DAYS.
        """
        raise NotImplementedError
