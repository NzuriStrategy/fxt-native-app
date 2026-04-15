"""
scoring.weights — Configurable weights for each signal type.

Weights are multiplied by signal confidence to compute each signal's
contribution to the final score. They are normalised internally so the
total score always falls in [0, 100].

Adjust these values based on observed conversion rates from lead review.
Higher weight = this signal is a stronger predictor of fit.
"""

from __future__ import annotations

from signals.base import SignalType

# Weights are positive floats. Absolute values don't matter —
# only relative magnitudes. Normalisation happens in Scorer.
SIGNAL_WEIGHTS: dict[SignalType, float] = {
    # Warehouse signals (highest weight — most direct indicators)
    SignalType.DENSIFICATION_KEYWORD: 10.0,
    SignalType.CAPACITY_CONSTRAINT_MENTIONED: 9.0,
    SignalType.WAREHOUSE_EXPANSION_MENTIONED: 7.0,
    SignalType.WMS_EVALUATION: 8.0,
    SignalType.SKU_GROWTH_MENTIONED: 6.0,

    # Employment signals (medium weight — leading indicators)
    SignalType.VP_SUPPLY_CHAIN_HIRE: 7.0,
    SignalType.LOGISTICS_HIRING_SURGE: 5.0,
    SignalType.WAREHOUSE_OPS_HIRING: 4.0,

    # Real-estate signals (lower weight — longer time horizon)
    SignalType.NEW_LEASE_SIGNED: 5.0,
    SignalType.DC_CONSTRUCTION_MENTIONED: 3.0,
    SignalType.THIRD_PARTY_LOGISTICS: 4.0,
}

# Signals older than this many days are decayed (multiplied by DECAY_FACTOR)
SIGNAL_STALENESS_DAYS: int = 90
DECAY_FACTOR: float = 0.5
