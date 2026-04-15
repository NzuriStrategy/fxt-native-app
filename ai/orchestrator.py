"""
ai.orchestrator — Batches qualified leads through the LLM enrichment stage.
"""

from __future__ import annotations

from scoring.base import ScoredLead
from utils.logging import get_logger
from .base import AbstractAIClient, EnrichedLead
from .classifier import LeadClassifier
from .enricher import AnthropicClient

logger = get_logger(__name__)


class AIEnrichmentOrchestrator:
    """
    Enriches a list of qualified ScoredLead objects by running each through
    the LeadClassifier.

    Batching: calls are made sequentially by default to stay within rate limits.
    TODO: Add async batching with concurrency cap for throughput.
    """

    def __init__(self, client: AbstractAIClient | None = None) -> None:
        self._client = client or AnthropicClient()
        self._classifier = LeadClassifier(self._client)

    def run(self, leads: list[ScoredLead]) -> list[EnrichedLead]:
        """
        Enrich all leads. Failures on individual leads are logged and skipped
        rather than aborting the whole batch.
        """
        enriched: list[EnrichedLead] = []

        for lead in leads:
            try:
                result = self._classifier.classify(lead)
                enriched.append(result)
                logger.info(
                    "ai.enriched",
                    company_id=lead.company_id,
                    confidence=result.confidence_class,
                    prompt_tokens=result.prompt_tokens,
                )
            except Exception as exc:
                logger.error("ai.enrichment_failed", company_id=lead.company_id, error=str(exc))

        return enriched
