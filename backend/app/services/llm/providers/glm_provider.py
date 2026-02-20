"""
GLM-4.7 (Zhipu AI) LLM provider implementation.

Uses the OpenAI-compatible API endpoint provided by Zhipu AI.
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


class GLMProvider:
    """GLM-4.7 (Zhipu AI) LLM provider.

    Zhipu AI exposes an OpenAI-compatible chat completions API,
    so we use the openai SDK pointed at their base URL.

    Supports:
    - glm-4-plus: Best general-purpose model
    - glm-4-flash: Fast, cost-effective for simpler tasks
    """

    provider_name = "glm"

    DEFAULT_MODEL = "glm-4-plus"
    BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    # Pricing per 1M tokens (approximate, in USD)
    PRICING = {
        "glm-4-plus": {"input": 0.70, "output": 0.70},
        "glm-4-flash": {"input": 0.01, "output": 0.01},
    }

    def __init__(self, api_key: str) -> None:
        """Initialize the GLM provider.

        Args:
            api_key: Zhipu AI API key
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
        """Generate a completion using GLM models.

        Args:
            messages: Conversation history
            model: Model identifier (uses glm-4-plus if None)
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

            logger.debug(f"GLM request: model={model}, messages={len(messages)}")

            response = await self._client.chat.completions.create(**request_params)

            latency_ms = (time.perf_counter() - start_time) * 1000
            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            finish_reason = response.choices[0].finish_reason

            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            logger.debug(
                f"GLM response: tokens={input_tokens + output_tokens}, "
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
            logger.warning(f"GLM rate limit error: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"GLM API error: {e}")
            raise ProviderError(provider=self.provider_name, detail=str(e)) from e

        except Exception as e:
            logger.error(f"Unexpected error in GLM provider: {e}")
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
        """Stream completion tokens from GLM.

        Args:
            messages: Conversation history
            model: Model identifier (uses glm-4-plus if None)
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
            logger.warning(f"GLM rate limit during streaming: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"GLM API error during streaming: {e}")
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
