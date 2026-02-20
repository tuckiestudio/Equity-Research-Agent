"""Task router for multi-LLM provider management.

The router maps task types to specific provider+model combinations,
providing intelligent routing with fallback handling.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Optional

from app.core.errors import ProviderError, RateLimitError
from app.core.logging import get_logger
from app.services.llm.protocols import LLMProvider
from app.services.llm.types import LLMMessage, LLMResponse, TaskType

logger = get_logger(__name__)


# Default routing table — maps task types to (provider, model) pairs
# This balances cost vs. capability for different analysis tasks
DEFAULT_ROUTING: dict[TaskType, tuple[str, str]] = {
    TaskType.THESIS_GENERATION: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.THESIS_UPDATE: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.NEWS_ANALYSIS: ("openai", "gpt-4o"),
    TaskType.ASSUMPTION_GENERATION: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.COMPANY_COMPARISON: ("openai", "gpt-4o"),
    TaskType.NOTE_EXTRACTION: ("openai", "gpt-4o-mini"),
    TaskType.WATCH_ITEMS: ("openai", "gpt-4o"),
    TaskType.QUICK_SUMMARY: ("openai", "gpt-4o-mini"),
    TaskType.DATA_FORMATTING: ("openai", "gpt-4o-mini"),
}

# Fallback chains for each provider
FALLBACK_CHAINS: dict[str, list[str]] = {
    "anthropic": ["openai", "kimi", "glm"],
    "openai": ["anthropic", "kimi", "glm"],
    "glm": ["openai", "anthropic"],
    "kimi": ["anthropic", "openai"],
}


class LLMRouter:
    """Intelligent router for multi-LLM provider management.

    The router handles:
    - Task type → provider+model mapping
    - Provider registration and lookup
    - Automatic fallback on provider failures
    - Runtime route overrides for testing/configuration
    """

    def __init__(self) -> None:
        """Initialize the router with default routing configuration."""
        self._providers: dict[str, LLMProvider] = {}
        self._routing: dict[TaskType, tuple[str, str]] = dict(DEFAULT_ROUTING)

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register an LLM provider instance.

        Args:
            name: Provider identifier (e.g., "openai", "anthropic")
            provider: Provider instance implementing LLMProvider protocol
        """
        self._providers[name] = provider
        logger.info(f"Registered LLM provider: {name}")

    def get_providers(self) -> list[str]:
        """Get list of registered provider names.

        Returns:
            List of provider identifiers
        """
        return list(self._providers.keys())

    def route(self, task_type: TaskType) -> tuple[str, str]:
        """Get the (provider_name, model_name) for a task type.

        Args:
            task_type: The type of analysis task

        Returns:
            Tuple of (provider_name, model_name)

        Raises:
            ProviderError: If task_type is not in routing table
        """
        if task_type not in self._routing:
            raise ProviderError(
                provider="router",
                detail=f"No routing configured for task type: {task_type}",
            )

        return self._routing[task_type]

    def override_route(self, task_type: TaskType, provider: str, model: str) -> None:
        """Override the routing for a specific task type.

        This is useful for testing or runtime configuration changes.

        Args:
            task_type: The task type to override
            provider: The provider to use
            model: The model to use
        """
        self._routing[task_type] = (provider, model)
        logger.info(f"Override route: {task_type} → {provider}/{model}")

    def reset_route(self, task_type: Optional[TaskType] = None) -> None:
        """Reset routing to defaults.

        Args:
            task_type: If provided, reset only this task type.
                      If None, reset all routes to defaults.
        """
        if task_type is None:
            self._routing = dict(DEFAULT_ROUTING)
            logger.info("Reset all routes to defaults")
        elif task_type in DEFAULT_ROUTING:
            self._routing[task_type] = DEFAULT_ROUTING[task_type]
            logger.info(f"Reset route for {task_type} to default")

    async def complete(
        self,
        task_type: TaskType,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Route a completion request to the appropriate provider+model.

        Implements automatic fallback if the primary provider fails.

        Args:
            task_type: The type of analysis task
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Request JSON output format

        Returns:
            LLMResponse with content, tokens, latency, and cost

        Raises:
            ProviderError: If all providers in the fallback chain fail
        """
        provider_name, model = self.route(task_type)

        # Get fallback chain for this provider
        fallback_chain = FALLBACK_CHAINS.get(provider_name, [])

        # Try primary provider first
        last_error = None
        providers_to_try = [provider_name] + fallback_chain

        for try_provider_name in providers_to_try:
            if try_provider_name not in self._providers:
                logger.warning(
                    f"Provider {try_provider_name} not registered, skipping"
                )
                continue

            try:
                provider = self._providers[try_provider_name]
                logger.debug(
                    f"Routing {task_type} to {try_provider_name}/{model} "
                    f"(original route: {provider_name})"
                )
                return await provider.complete(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )

            except (ProviderError, RateLimitError) as e:
                logger.warning(
                    f"Provider {try_provider_name} failed: {e}. "
                    f"Trying fallback..."
                )
                last_error = e
                continue

        # All providers failed
        raise ProviderError(
            provider="router",
            detail=f"All providers failed for task {task_type}. Last error: {last_error}",
        )

    async def complete_stream(
        self,
        task_type: TaskType,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream a completion request to the appropriate provider+model.

        Note: Streaming does not implement automatic fallback due to the
        complexity of mid-stream provider switching.

        Args:
            task_type: The type of analysis task
            messages: Conversation history
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Yields:
            Individual text chunks as they arrive

        Raises:
            ProviderError: If the primary provider fails
        """
        provider_name, model = self.route(task_type)

        if provider_name not in self._providers:
            raise ProviderError(
                provider="router",
                detail=f"Provider {provider_name} not registered",
            )

        provider = self._providers[provider_name]
        logger.debug(f"Streaming {task_type} to {provider_name}/{model}")

        async for chunk in provider.complete_stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
