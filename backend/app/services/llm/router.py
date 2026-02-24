"""Task router for multi-LLM provider management.

The router maps task types to specific provider+model combinations,
providing intelligent routing with fallback handling.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Optional, TYPE_CHECKING

from app.core.config import settings
from app.core.errors import ProviderError, RateLimitError
from app.core.logging import get_logger
from app.services.llm.protocols import LLMProvider
from app.services.llm.types import LLMMessage, LLMResponse, TaskType

if TYPE_CHECKING:
    from app.models.user_settings import UserSettings

logger = get_logger(__name__)


# Default routing table — maps task types to (provider, model) pairs
# This balances cost vs. capability for different analysis tasks
#
# For direct providers (anthropic, openai), model names are the provider's native names
# For meta-providers (openrouter), model names include provider prefix (e.g., "anthropic/claude-3-opus")
#
# DEFAULT: Uses OpenRouter free models for all tasks to minimize costs.
# Users can override via llm_routing_preferences in UserSettings for premium models.
DEFAULT_ROUTING: dict[TaskType, tuple[str, str]] = {
    # Complex reasoning tasks - use free Llama/Mistral models
    TaskType.THESIS_GENERATION: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.THESIS_UPDATE: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.NEWS_ANALYSIS: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.ASSUMPTION_GENERATION: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.COMPANY_COMPARISON: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    # Lighter tasks - use free models
    TaskType.NOTE_EXTRACTION: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.WATCH_ITEMS: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.QUICK_SUMMARY: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
    TaskType.DATA_FORMATTING: ("openrouter", "meta-llama/llama-3-8b-instruct:free"),
}

# Model name mappings for meta-providers (OpenRouter, Chutes)
# These map native model names to the meta-provider's format
OPENROUTER_MODEL_MAP: dict[str, str] = {
    # Anthropic models
    "claude-sonnet-4-20250514": "anthropic/claude-3-sonnet",
    "claude-3-opus": "anthropic/claude-3-opus",
    "claude-3-haiku": "anthropic/claude-3-haiku",
    # OpenAI models
    "gpt-4o": "openai/gpt-4o",
    "gpt-4-turbo": "openai/gpt-4-turbo",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
}

CHUTES_MODEL_MAP: dict[str, str] = {
    # Llama models (closest equivalents to GPT-4o-mini for quick tasks)
    "gpt-4o-mini": "llama-3-8b-instruct",
    "gpt-4o": "llama-3-70b-instruct",
    # Mistral models
    "claude-sonnet-4-20250514": "mixtral-8x7b-instruct",
}

# Fallback chains for each provider
# When primary provider fails, try these in order
# OpenRouter is prioritized as fallback since it offers free models and serves as a meta-provider
FALLBACK_CHAINS: dict[str, list[str]] = {
    "anthropic": ["openrouter", "openai", "kimi", "glm"],
    "openai": ["openrouter", "anthropic", "kimi", "glm"],
    "openrouter": ["chutes", "kimi", "glm"],  # OpenRouter fallbacks exclude itself
    "glm": ["openrouter", "openai", "anthropic"],
    "kimi": ["openrouter", "anthropic", "openai"],
    "chutes": ["openrouter", "openai", "anthropic"],
}


class LLMRouter:
    """Intelligent router for multi-LLM provider management.

    The router handles:
    - Task type → provider+model mapping
    - Provider registration and lookup
    - Automatic fallback on provider failures
    - Runtime route overrides for testing/configuration
    """

    def __init__(self, user_settings: Optional[UserSettings] = None) -> None:
        """Initialize the router with default routing configuration.

        Args:
            user_settings: Optional user settings for API key lookup.
                          If not provided, uses global settings.
        """
        self._providers: dict[str, LLMProvider] = {}
        self._routing: dict[TaskType, tuple[str, str]] = dict(DEFAULT_ROUTING)
        self._user_settings = user_settings

        # Auto-register providers based on available API keys
        self._initialize_providers(user_settings)

        # Apply user routing preferences if available
        self._apply_user_routing_preferences()

    def _initialize_providers(self, user_settings: Optional[UserSettings] = None) -> None:
        """Initialize LLM providers based on available API keys.

        Args:
            user_settings: Optional user settings for API key lookup
        """
        # Get API keys from user settings or global config
        anthropic_key = (user_settings.anthropic_api_key if user_settings else None) or settings.ANTHROPIC_API_KEY
        openai_key = (user_settings.openai_api_key if user_settings else None) or settings.OPENAI_API_KEY
        glm_key = (user_settings.glm_api_key if user_settings else None) or settings.GLM_API_KEY
        kimi_key = (user_settings.kimi_api_key if user_settings else None) or settings.KIMI_API_KEY
        openrouter_key = (user_settings.openrouter_api_key if user_settings else None) or settings.OPENROUTER_API_KEY
        chutes_key = (user_settings.chutes_api_key if user_settings else None) or settings.CHUTES_API_KEY

        # Register providers with available API keys
        if anthropic_key:
            from app.services.llm.providers.anthropic_provider import AnthropicProvider
            self.register_provider("anthropic", AnthropicProvider(anthropic_key))
            logger.info("Registered Anthropic provider")

        if openai_key:
            from app.services.llm.providers.openai_provider import OpenAIProvider
            self.register_provider("openai", OpenAIProvider(openai_key))
            logger.info("Registered OpenAI provider")

        if glm_key:
            from app.services.llm.providers.glm_provider import GLMProvider
            self.register_provider("glm", GLMProvider(glm_key))
            logger.info("Registered GLM provider")

        if kimi_key:
            from app.services.llm.providers.kimi_provider import KimiProvider
            self.register_provider("kimi", KimiProvider(kimi_key))
            logger.info("Registered Kimi provider")

        if openrouter_key:
            from app.services.llm.providers.openrouter_provider import OpenRouterProvider
            self.register_provider("openrouter", OpenRouterProvider(openrouter_key))
            logger.info("Registered OpenRouter provider")

        if chutes_key:
            from app.services.llm.providers.chutes_provider import ChutesProvider
            self.register_provider("chutes", ChutesProvider(chutes_key))
            logger.info("Registered Chutes provider")

        if not self._providers:
            logger.warning("No LLM providers registered - no API keys available")

    def _apply_user_routing_preferences(self) -> None:
        """Apply user's custom routing preferences from settings."""
        if not self._user_settings or not self._user_settings.llm_routing_preferences:
            return

        preferences = self._user_settings.llm_routing_preferences
        for task_type_str, route in preferences.items():
            try:
                task_type = TaskType(task_type_str)
                provider = route.get("provider")
                model = route.get("model")
                if provider and model and provider in self._providers:
                    self._routing[task_type] = (provider, model)
                    logger.info(f"Applied user route for {task_type.value}: {provider}/{model}")
            except ValueError:
                logger.warning(f"Unknown task type in user preferences: {task_type_str}")

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

            # Translate model name for meta-providers (OpenRouter, Chutes)
            actual_model = model
            if try_provider_name == "openrouter" and model in OPENROUTER_MODEL_MAP:
                actual_model = OPENROUTER_MODEL_MAP[model]
                logger.debug(f"Translated model {model} → {actual_model} for OpenRouter")
            elif try_provider_name == "chutes" and model in CHUTES_MODEL_MAP:
                actual_model = CHUTES_MODEL_MAP[model]
                logger.debug(f"Translated model {model} → {actual_model} for Chutes")

            try:
                provider = self._providers[try_provider_name]
                logger.debug(
                    f"Routing {task_type} to {try_provider_name}/{actual_model} "
                    f"(original route: {provider_name}/{model})"
                )
                return await provider.complete(
                    messages=messages,
                    model=actual_model,
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

        # Translate model name for meta-providers (OpenRouter, Chutes)
        actual_model = model
        if provider_name == "openrouter" and model in OPENROUTER_MODEL_MAP:
            actual_model = OPENROUTER_MODEL_MAP[model]
            logger.debug(f"Translated model {model} → {actual_model} for OpenRouter")
        elif provider_name == "chutes" and model in CHUTES_MODEL_MAP:
            actual_model = CHUTES_MODEL_MAP[model]
            logger.debug(f"Translated model {model} → {actual_model} for Chutes")

        provider = self._providers[provider_name]
        logger.debug(f"Streaming {task_type} to {provider_name}/{actual_model}")

        async for chunk in provider.complete_stream(
            messages=messages,
            model=actual_model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
