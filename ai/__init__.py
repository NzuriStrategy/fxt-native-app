"""
ai — LLM-based enrichment and classification of qualified leads.

Responsibilities
----------------
- Send ScoredLead objects to an LLM (Anthropic Claude by default)
- Produce structured outputs:
    - narrative_summary: why this company is a fit (2–3 sentences)
    - confidence_class: HIGH / MEDIUM / LOW
    - outreach_angle: recommended first-touch message framing
- Handle token budgeting, prompt caching, and cost logging
- Provide a fallback path when the AI stage is skipped (--skip-ai)

The AIEnrichmentOrchestrator batches calls to respect rate limits.
The LeadClassifier wraps the raw Anthropic SDK call with structured output parsing.
"""

from .orchestrator import AIEnrichmentOrchestrator
from .base import AbstractAIClient, EnrichedLead

__all__ = [
    "AIEnrichmentOrchestrator",
    "AbstractAIClient",
    "EnrichedLead",
]
