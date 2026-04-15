"""
ai.base — Abstract contract for AI clients and the EnrichedLead output type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from scoring.base import ScoredLead


class ConfidenceClass(str, Enum):
    """LLM-assigned confidence classification for a lead."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EnrichedLead:
    """
    A ScoredLead augmented with LLM-generated analysis.

    This is the final data shape written to storage and consumed by
    downstream tools (CRM export, outreach sequencer, sales dashboard).
    """

    # Original scored lead — preserved for traceability
    scored_lead: ScoredLead

    # LLM outputs
    narrative_summary: str  # 2–3 sentences: why this company is a fit
    confidence_class: ConfidenceClass
    outreach_angle: str  # Recommended framing for first-touch message

    # Token usage tracking for cost visibility
    prompt_tokens: int = 0
    completion_tokens: int = 0

    enriched_at: datetime = field(default_factory=datetime.utcnow)
    model_used: str = ""

    # Convenience passthroughs
    @property
    def company_id(self) -> str:
        return self.scored_lead.company_id

    @property
    def score(self) -> float:
        return self.scored_lead.score


class AbstractAIClient(ABC):
    """
    Thin abstraction over an LLM provider (Anthropic Claude, OpenAI, etc.).

    Allows the enricher to be tested with a mock client and swapped
    between providers without changing business logic.
    """

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
    ) -> tuple[str, int, int]:
        """
        Send a message to the LLM and return the response text plus token counts.

        Returns
        -------
        tuple[str, int, int]
            (response_text, prompt_tokens, completion_tokens)
        """
        ...
