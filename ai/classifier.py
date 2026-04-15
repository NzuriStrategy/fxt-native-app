"""
ai.classifier — LLM-powered lead classifier using the Anthropic SDK.

Sends a ScoredLead's signal evidence to Claude and asks it to:
  1. Validate the automated score with a confidence classification
  2. Write a 2–3 sentence narrative explaining the fit
  3. Suggest an outreach angle

Prompt design principles:
- Structured output via XML tags for deterministic parsing
- System prompt cached with Anthropic prompt caching (beta) to reduce cost
- Temperature = 0.0 for reproducible outputs
- Evidence snippets give the model grounding; it doesn't hallucinate signals

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from config import settings
from utils.logging import get_logger
from .base import AbstractAIClient, ConfidenceClass, EnrichedLead
from scoring.base import ScoredLead

logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are an expert B2B sales analyst specialising in warehouse operations
and supply chain infrastructure. Your task is to evaluate lead intelligence
data about companies and determine whether they are likely candidates for
warehouse densification solutions.

You will receive:
- A company name and description
- Signal evidence: excerpts from their website, job postings, and news articles
- An automated lead score (0–100)

Respond in the following XML format only:
<analysis>
  <confidence_class>HIGH|MEDIUM|LOW</confidence_class>
  <narrative_summary>2-3 sentences explaining why this company fits.</narrative_summary>
  <outreach_angle>One sentence: the most compelling angle for a first conversation.</outreach_angle>
</analysis>
""".strip()


class LeadClassifier:
    """
    Wraps the Anthropic API call with prompt construction and response parsing.
    """

    def __init__(self, client: AbstractAIClient) -> None:
        self._client = client

    def classify(self, lead: ScoredLead) -> EnrichedLead:
        """
        Build a prompt from the lead's signals, call the LLM, parse the response.

        TODO: Implement prompt construction, API call, and XML response parsing.

        Pseudocode:
          user_message = build_user_message(lead)
          response, prompt_tokens, completion_tokens = self._client.complete(
              system_prompt=SYSTEM_PROMPT,
              user_message=user_message,
              max_tokens=settings.ai.max_tokens,
          )
          confidence_class, narrative, angle = parse_xml_response(response)
          return EnrichedLead(
              scored_lead=lead,
              narrative_summary=narrative,
              confidence_class=confidence_class,
              outreach_angle=angle,
              prompt_tokens=prompt_tokens,
              completion_tokens=completion_tokens,
              model_used=settings.ai.default_model,
          )
        """
        raise NotImplementedError

    def _build_user_message(self, lead: ScoredLead) -> str:
        """
        TODO: Format the lead's signals and score into a structured prompt.
        """
        raise NotImplementedError

    def _parse_response(self, response: str) -> tuple[ConfidenceClass, str, str]:
        """
        TODO: Parse the XML-tagged response and return
        (confidence_class, narrative_summary, outreach_angle).
        """
        raise NotImplementedError
