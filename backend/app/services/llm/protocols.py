from __future__ import annotations
from typing import Optional, Any
"""Protocol definitions for LLM providers.

All LLM providers must implement the LLMProvider protocol to ensure
consistent behavior across different AI services.
"""


from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from app.services.llm.types import LLMMessage, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM providers must implement.

    This ensures hot-swappable providers with consistent behavior.
    """

    provider_name: str

    async def complete(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion for the given messages.

        Args:
            messages: Conversation history with system/user/assistant roles
            model: Model identifier (uses provider default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output format

        Returns:
            LLMResponse with content, tokens, latency, and cost

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting (HTTP 429)
        """
        ...

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream completion tokens as they are generated.

        Args:
            messages: Conversation history
            model: Model identifier (uses provider default if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Individual text chunks as they arrive

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting
        """
        ...
