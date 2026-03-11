"""
Chutes.ai LLM provider implementation.

Chutes provides fast, affordable inference for open-source models
with a focus on Llama, Mistral, and other open-weight models.
"""
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


class ChutesProvider:
    """Chutes.ai provider for open-source model inference.

    Chutes specializes in:
    - Llama 3 (8B, 70B)
    - Mistral models
    - Qwen models
    - Other open-weight models

    Website: https://chutes.ai
    """

    provider_name = "chutes"

    DEFAULT_MODEL = "llama-3-8b-instruct"
    BASE_URL = "https://chutes.ai/api/v1"

    # Pricing per 1M tokens (approximate, in USD)
    # Chutes offers competitive pricing on open models
    PRICING = {
        "llama-3-8b-instruct": {"input": 0.20, "output": 0.20},
        "llama-3-70b-instruct": {"input": 0.90, "output": 0.90},
        "llama-3.1-8b-instruct": {"input": 0.20, "output": 0.20},
        "llama-3.1-70b-instruct": {"input": 0.90, "output": 0.90},
        "llama-3.1-405b-instruct": {"input": 3.00, "output": 3.00},
        "mistral-7b-instruct": {"input": 0.20, "output": 0.20},
        "mixtral-8x7b-instruct": {"input": 0.60, "output": 0.60},
        "qwen-2.5-72b-instruct": {"input": 0.90, "output": 0.90},
    }

    def __init__(self, api_key: str) -> None:
        """Initialize the Chutes provider.

        Args:
            api_key: Chutes.ai API key (get from https://chutes.ai/)
        """
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
        )
        self._api_key = api_key

    async def complete(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion using Chutes models.

        Args:
            messages: Conversation history
            model: Model identifier (e.g., "llama-3-70b-instruct")
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output format

        Returns:
            LLMResponse with content, tokens, latency, and cost

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting
        """
        model = model or self.DEFAULT_MODEL
        start_time = time.perf_counter()

        try:
            openai_messages = [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ]

            request_params = {
                "model": model,
                "messages": openai_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if json_mode:
                request_params["response_format"] = {"type": "json_object"}

            logger.debug(f"Chutes request: model={model}, messages={len(messages)}")

            response = await self._client.chat.completions.create(**request_params)

            latency_ms = (time.perf_counter() - start_time) * 1000
            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            finish_reason = response.choices[0].finish_reason

            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            logger.debug(
                f"Chutes response: tokens={input_tokens + output_tokens}, "
                f"latency={latency_ms:.2f}ms, cost=${cost_usd:.6f}"
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
            logger.warning(f"Chutes rate limit error: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"Chutes API error: {e}")
            raise ProviderError(provider=self.provider_name, detail=str(e)) from e

        except Exception as e:
            logger.error(f"Unexpected error in Chutes provider: {e}")
            raise ProviderError(
                provider=self.provider_name, detail=f"Unexpected error: {e}"
            ) from e

    async def complete_stream(
        self,
        messages: list[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream completion tokens from Chutes.

        Args:
            messages: Conversation history
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Individual text chunks

        Raises:
            ProviderError: For API errors
            RateLimitError: For rate limiting
        """
        model = model or self.DEFAULT_MODEL

        try:
            openai_messages = [
                {"role": msg.role.value, "content": msg.content} for msg in messages
            ]

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
            logger.warning(f"Chutes rate limit during streaming: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"Chutes API error during streaming: {e}")
            raise ProviderError(provider=self.provider_name, detail=str(e)) from e

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost in USD."""
        if model not in self.PRICING:
            return 0.0
        pricing = self.PRICING[model]
        return (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]
