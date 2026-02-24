"""
OpenRouter LLM provider implementation.

OpenRouter provides unified access to 100+ LLM models from different providers
(Claude, GPT-4, Llama, Mistral, etc.) through a single API.
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


class OpenRouterProvider:
    """OpenRouter provider for multi-model access.

    OpenRouter aggregates models from multiple providers:
    - Anthropic (Claude)
    - OpenAI (GPT-4, GPT-3.5)
    - Meta (Llama)
    - Mistral AI
    - Google (Gemini)
    - And many more

    Website: https://openrouter.ai
    """

    provider_name = "openrouter"

    DEFAULT_MODEL = "meta-llama/llama-3-8b-instruct:free"
    BASE_URL = "https://openrouter.ai/api/v1"

    # Popular models and their pricing per 1M tokens (approximate, in USD)
    # OpenRouter passes through provider pricing
    # Free models are listed first - these are great for development and testing
    PRICING = {
        # === FREE MODELS ===
        "meta-llama/llama-3-8b-instruct:free": {"input": 0.0, "output": 0.0},
        # Note: OpenRouter periodically adds more free models - check openrouter.ai/models
        # Other commonly free/very-low-cost models:
        "google/gemma-7b-it:free": {"input": 0.0, "output": 0.0},
        "mistralai/mistral-7b-instruct:free": {"input": 0.0, "output": 0.0},

        # === PREMIUM MODELS ===
        # Anthropic
        "anthropic/claude-3-opus": {"input": 15.0, "output": 75.0},
        "anthropic/claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
        # OpenAI
        "openai/gpt-4o": {"input": 5.0, "output": 15.0},
        "openai/gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "openai/gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        # Meta
        "meta-llama/llama-3-70b-instruct": {"input": 0.80, "output": 0.80},
        "meta-llama/llama-3-8b-instruct": {"input": 0.10, "output": 0.10},
        # Mistral
        "mistralai/mistral-large": {"input": 4.0, "output": 12.0},
        "mistralai/mixtral-8x7b-instruct": {"input": 0.60, "output": 0.60},
        # Google
        "google/gemini-pro-1.5": {"input": 2.5, "output": 7.5},
    }

    def __init__(self, api_key: str) -> None:
        """Initialize the OpenRouter provider.

        Args:
            api_key: OpenRouter API key (get from https://openrouter.ai/keys)
        """
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            default_headers={
                "HTTP-Referer": "https://github.com/your-app",
                "X-Title": "Equity Research Agent",
            },
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
        """Generate a completion using OpenRouter models.

        Args:
            messages: Conversation history
            model: Model identifier (e.g., "anthropic/claude-3-opus")
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

            logger.debug(
                f"OpenRouter request: model={model}, messages={len(messages)}"
            )

            response = await self._client.chat.completions.create(**request_params)

            latency_ms = (time.perf_counter() - start_time) * 1000
            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            finish_reason = response.choices[0].finish_reason

            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)

            logger.debug(
                f"OpenRouter response: tokens={input_tokens + output_tokens}, "
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
            logger.warning(f"OpenRouter rate limit error: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"OpenRouter API error: {e}")
            raise ProviderError(provider=self.provider_name, detail=str(e)) from e

        except Exception as e:
            logger.error(f"Unexpected error in OpenRouter provider: {e}")
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
        """Stream completion tokens from OpenRouter.

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
            logger.warning(f"OpenRouter rate limit during streaming: {e}")
            raise RateLimitError(provider=self.provider_name) from e

        except OpenAIError as e:
            logger.error(f"OpenRouter API error during streaming: {e}")
            raise ProviderError(provider=self.provider_name, detail=str(e)) from e

    def _calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost in USD."""
        # Normalize model name (remove :free suffix for lookup)
        base_model = model.split(":")[0] if ":" in model else model

        # Try exact match first, then base model
        if model in self.PRICING:
            pricing = self.PRICING[model]
        elif base_model in self.PRICING:
            pricing = self.PRICING[base_model]
        else:
            # Unknown model - return 0 (OpenRouter will charge actual rate)
            return 0.0

        return (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]
