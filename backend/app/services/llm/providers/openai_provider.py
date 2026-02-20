"""OpenAI LLM provider implementation."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Optional

from openai import APIError as OpenAIError
from openai import AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from app.core.errors import ProviderError, RateLimitError
from app.core.logging import get_logger
from app.services.llm.types import LLMMessage, LLMResponse

logger = get_logger(__name__)


class OpenAIProvider:
    """OpenAI LLM provider with cost tracking and streaming support.

    Supports:
    - GPT-4o: Best for general analysis
    - GPT-4o-mini: Best for quick summaries and structured output
    - o3-mini: Best for complex reasoning
    """

    provider_name = "openai"

    DEFAULT_MODEL = "gpt-4o"

    # Pricing per 1M tokens (approximate, as of 2025)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o3-mini": {"input": 1.10, "output": 4.40},
    }

    def __init__(self, api_key: str) -> None:
        """Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key
        """
        self._client = AsyncOpenAI(api_key=api_key)
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
            model: Model identifier (uses gpt-4o if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output format

        Returns:
            LLMResponse with content, tokens, latency, and cost

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting (HTTP 429)
        """
        model = model or self.DEFAULT_MODEL
        start_time = time.perf_counter()

        try:
            # Convert LLMMessage to OpenAI format
            openai_messages = [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ]

            # Build request parameters
            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add JSON mode if requested
            if json_mode:
                request_params["response_format"] = {"type": "json_object"}

            logger.debug(f"OpenAI request: model={model}, messages={len(messages)}")

            response = await self._client.chat.completions.create(**request_params)

            # Calculate latency
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract content and metadata
            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            finish_reason = response.choices[0].finish_reason

            # Calculate cost
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            logger.debug(
                f"OpenAI response: tokens={input_tokens + output_tokens}, "
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

        except OpenAIRateLimitError as e:
            logger.warning(f"OpenAI rate limit error: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=str(e),
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {e}")
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
            model: Model identifier (uses gpt-4o if None)
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
            # Convert LLMMessage to OpenAI format
            openai_messages = [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ]

            logger.debug(f"OpenAI stream request: model={model}")

            stream = await self._client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

        except OpenAIRateLimitError as e:
            logger.warning(f"OpenAI rate limit error during streaming: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"OpenAI API error during streaming: {e}")
            raise ProviderError(
                provider=self.provider_name,
                detail=str(e),
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error in OpenAI streaming: {e}")
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
