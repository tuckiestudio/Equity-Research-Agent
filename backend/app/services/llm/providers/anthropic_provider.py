"""Anthropic (Claude) LLM provider implementation."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Optional

from anthropic import APIError as AnthropicError
from anthropic import AsyncAnthropic
from anthropic import RateLimitError as AnthropicRateLimitError

from app.core.errors import ProviderError, RateLimitError
from app.core.logging import get_logger
from app.services.llm.types import LLMMessage, LLMResponse, LLMRole

logger = get_logger(__name__)


class AnthropicProvider:
    """Anthropic (Claude) LLM provider with cost tracking and streaming support.

    Supports:
    - Claude Sonnet 4 (claude-sonnet-4-20250514): Best for complex reasoning
    - Claude Haiku 3 (claude-haiku-3-20250414): Best for quick summaries

    Note: Anthropic uses system as a separate parameter, not in messages list.
    """

    provider_name = "anthropic"

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    # Pricing per 1M tokens (approximate, as of 2025)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-3-20250414": {"input": 0.80, "output": 4.00},
    }

    def __init__(self, api_key: str) -> None:
        """Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
        """
        self._client = AsyncAnthropic(api_key=api_key)
        self._api_key = api_key

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
            model: Model identifier (uses claude-sonnet-4 if None)
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output (via prompt instruction)

        Returns:
            LLMResponse with content, tokens, latency, and cost

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting (HTTP 429)
        """
        model = model or self.DEFAULT_MODEL
        start_time = time.perf_counter()

        try:
            # Anthropic requires separating system prompt from messages
            system_prompt = ""
            anthropic_messages = []

            for msg in messages:
                if msg.role == LLMRole.SYSTEM:
                    # Combine multiple system messages
                    system_prompt += msg.content + "\n\n"
                else:
                    anthropic_messages.append(
                        {"role": msg.role.value, "content": msg.content}
                    )

            # For JSON mode, prepend instruction to system prompt
            if json_mode:
                system_prompt += "Output must be valid JSON only, no additional text.\n\n"

            logger.debug(
                f"Anthropic request: model={model}, messages={len(anthropic_messages)}, "
                f"system_prompt_length={len(system_prompt)}"
            )

            response = await self._client.messages.create(
                model=model,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract content and metadata
            content = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            finish_reason = response.stop_reason

            # Calculate cost
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            logger.debug(
                f"Anthropic response: tokens={input_tokens + output_tokens}, "
                f"latency={latency_ms:.2f}ms, cost=${cost_usd:.4f}"
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                finish_reason=finish_reason,
            )

        except AnthropicRateLimitError as e:
            logger.warning(f"Anthropic rate limit error: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except AnthropicError as e:
            logger.error(f"Anthropic API error: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=str(e),
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic provider: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=f"Unexpected error: {e}",
            ) from e

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
            model: Model identifier (uses claude-sonnet-4 if None)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Individual text chunks as they arrive

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting
        """
        model = model or self.DEFAULT_MODEL

        try:
            # Separate system prompt from messages
            system_prompt = ""
            anthropic_messages = []

            for msg in messages:
                if msg.role == LLMRole.SYSTEM:
                    system_prompt += msg.content + "\n\n"
                else:
                    anthropic_messages.append(
                        {"role": msg.role.value, "content": msg.content}
                    )

            logger.debug(f"Anthropic stream request: model={model}")

            async with self._client.messages.stream(
                model=model,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except AnthropicRateLimitError as e:
            logger.warning(f"Anthropic rate limit error during streaming: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except AnthropicError as e:
            logger.error(f"Anthropic API error during streaming: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=str(e),
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error in Anthropic streaming: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=f"Unexpected error during streaming: {e}",
            ) from e

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of a completion in USD.

        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if model not in self.PRICING:
            logger.warning(f"Unknown model {model} for cost calculation, returning 0")
            return 0.0

        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost
