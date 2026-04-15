"""
ai.enricher — Anthropic SDK client implementation.

Wraps anthropic.Anthropic with:
- Prompt caching (system prompt cached via cache_control beta header)
- Retry logic for rate limit / transient errors
- Cost logging per call

Not yet implemented — this is a structural stub.
"""

from __future__ import annotations

from config import settings
from utils.logging import get_logger
from .base import AbstractAIClient

logger = get_logger(__name__)


class AnthropicClient(AbstractAIClient):
    """
    Production AI client using the Anthropic Python SDK.

    Initialises a shared anthropic.Anthropic instance that reuses
    the HTTP connection pool across calls.
    """

    def __init__(self) -> None:
        # TODO: Initialise anthropic.Anthropic(api_key=...) here
        # Import deferred to avoid hard dependency when --skip-ai is set
        self._client = None  # placeholder
        self._model = settings.ai.default_model

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1024,
    ) -> tuple[str, int, int]:
        """
        TODO: Implement Anthropic API call with prompt caching.

        Pseudocode:
          response = self._client.messages.create(
              model=self._model,
              max_tokens=max_tokens,
              temperature=settings.ai.temperature,
              system=[{
                  "type": "text",
                  "text": system_prompt,
                  "cache_control": {"type": "ephemeral"},  # prompt caching
              }],
              messages=[{"role": "user", "content": user_message}],
          )
          text = response.content[0].text
          prompt_tokens = response.usage.input_tokens
          completion_tokens = response.usage.output_tokens
          logger.info("ai.call", model=self._model,
                      prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
          return text, prompt_tokens, completion_tokens
        """
        raise NotImplementedError
