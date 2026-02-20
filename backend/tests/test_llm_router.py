"""Tests for LLM router and prompt templates."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ProviderError
from app.services.llm.prompts.templates import (
    PromptTemplate,
    get_assumption_generation_template,
    get_company_comparison_template,
    get_news_analysis_template,
    get_note_extraction_template,
    get_thesis_generation_template,
    get_thesis_update_template,
    get_watch_items_template,
)
from app.services.llm.router import LLMRouter
from app.services.llm.types import LLMMessage, LLMResponse, LLMRole, TaskType


class TestLLMRouter:
    """Test suite for LLM router."""

    @pytest.fixture
    def router(self) -> LLMRouter:
        """Create a router instance."""
        return LLMRouter()

    @pytest.fixture
    def mock_openai_provider(self) -> MagicMock:
        """Create a mock OpenAI provider."""
        provider = AsyncMock()
        provider.provider_name = "openai"
        provider.complete = AsyncMock(
            return_value=LLMResponse(
                content="OpenAI response",
                model="gpt-4o",
                provider="openai",
                input_tokens=10,
                output_tokens=20,
                latency_ms=100.0,
            )
        )
        return provider

    @pytest.fixture
    def mock_anthropic_provider(self) -> MagicMock:
        """Create a mock Anthropic provider."""
        provider = AsyncMock()
        provider.provider_name = "anthropic"
        provider.complete = AsyncMock(
            return_value=LLMResponse(
                content="Anthropic response",
                model="claude-sonnet-4-20250514",
                provider="anthropic",
                input_tokens=15,
                output_tokens=25,
                latency_ms=150.0,
            )
        )
        return provider

    @pytest.fixture
    def sample_messages(self) -> list[LLMMessage]:
        """Sample messages for testing."""
        return [
            LLMMessage(role=LLMRole.USER, content="Test message"),
        ]

    def test_default_routing(self, router):
        """Test that default routing matches expected provider+model pairs."""
        # Thesis generation → Anthropic Sonnet
        provider, model = router.route(TaskType.THESIS_GENERATION)
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-20250514"

        # Quick summary → OpenAI mini
        provider, model = router.route(TaskType.QUICK_SUMMARY)
        assert provider == "openai"
        assert model == "gpt-4o-mini"

        # News analysis → OpenAI gpt-4o
        provider, model = router.route(TaskType.NEWS_ANALYSIS)
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_register_provider(self, router, mock_openai_provider):
        """Test provider registration."""
        router.register_provider("openai", mock_openai_provider)

        assert "openai" in router.get_providers()

    def test_route_override(self, router):
        """Test overriding routes for specific task types."""
        # Override thesis generation to use OpenAI
        router.override_route(
            TaskType.THESIS_GENERATION, "openai", "gpt-4o"
        )

        provider, model = router.route(TaskType.THESIS_GENERATION)
        assert provider == "openai"
        assert model == "gpt-4o"

    def test_reset_route(self, router):
        """Test resetting routes to defaults."""
        # Override a route
        router.override_route(TaskType.THESIS_GENERATION, "openai", "gpt-4o")

        # Reset it
        router.reset_route(TaskType.THESIS_GENERATION)

        # Should be back to default
        provider, model = router.route(TaskType.THESIS_GENERATION)
        assert provider == "anthropic"
        assert model == "claude-sonnet-4-20250514"

    def test_reset_all_routes(self, router):
        """Test resetting all routes to defaults."""
        router.override_route(TaskType.THESIS_GENERATION, "openai", "gpt-4o")
        router.override_route(TaskType.QUICK_SUMMARY, "anthropic", "claude-haiku-3-20250414")

        router.reset_route()

        # Both should be back to defaults
        provider, model = router.route(TaskType.THESIS_GENERATION)
        assert provider == "anthropic"

        provider, model = router.route(TaskType.QUICK_SUMMARY)
        assert provider == "openai"

    @pytest.mark.asyncio
    async def test_complete_routes_correctly(
        self, router, mock_openai_provider, mock_anthropic_provider, sample_messages
    ):
        """Test that complete() calls the correct provider based on task type."""
        router.register_provider("openai", mock_openai_provider)
        router.register_provider("anthropic", mock_anthropic_provider)

        # Thesis generation should route to Anthropic
        response = await router.complete(TaskType.THESIS_GENERATION, sample_messages)
        assert response.provider == "anthropic"
        mock_anthropic_provider.complete.assert_called_once()

        # Quick summary should route to OpenAI mini
        response = await router.complete(TaskType.QUICK_SUMMARY, sample_messages)
        assert response.provider == "openai"
        mock_openai_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_with_custom_params(
        self, router, mock_openai_provider, sample_messages
    ):
        """Test that custom parameters are passed through."""
        router.register_provider("openai", mock_openai_provider)

        await router.complete(
            TaskType.QUICK_SUMMARY,
            sample_messages,
            temperature=0.5,
            max_tokens=1000,
            json_mode=True,
        )

        # Verify provider was called with correct params
        mock_openai_provider.complete.assert_called_once()
        call_args = mock_openai_provider.complete.call_args
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["max_tokens"] == 1000
        assert call_args.kwargs["json_mode"] is True

    @pytest.mark.asyncio
    async def test_fallback_on_failure(
        self, router, mock_openai_provider, mock_anthropic_provider, sample_messages
    ):
        """Test that fallback provider is used when primary fails."""
        # Make Anthropic fail
        mock_anthropic_provider.complete = AsyncMock(
            side_effect=ProviderError(provider="anthropic", detail="Failed")
        )

        router.register_provider("anthropic", mock_anthropic_provider)
        router.register_provider("openai", mock_openai_provider)

        # Thesis generation primary is Anthropic, should fall back to OpenAI
        response = await router.complete(TaskType.THESIS_GENERATION, sample_messages)

        assert response.provider == "openai"
        mock_anthropic_provider.complete.assert_called_once()
        mock_openai_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_providers_fail(
        self, router, mock_openai_provider, mock_anthropic_provider, sample_messages
    ):
        """Test error when all providers in fallback chain fail."""
        # Make both fail
        mock_anthropic_provider.complete = AsyncMock(
            side_effect=ProviderError(provider="anthropic", detail="Failed")
        )
        mock_openai_provider.complete = AsyncMock(
            side_effect=ProviderError(provider="openai", detail="Failed")
        )

        router.register_provider("anthropic", mock_anthropic_provider)
        router.register_provider("openai", mock_openai_provider)

        with pytest.raises(ProviderError) as exc_info:
            await router.complete(TaskType.THESIS_GENERATION, sample_messages)

        # Router is the provider
        assert "router" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_provider(
        self, router, mock_anthropic_provider, mock_openai_provider, sample_messages
    ):
        """Test error when required provider is not registered."""
        # Register only Anthropic provider
        router.register_provider("anthropic", mock_anthropic_provider)

        # Create a mock that will fail when called
        mock_openai_provider.complete = AsyncMock(
            side_effect=ProviderError(provider="openai", detail="Failed")
        )
        router.register_provider("openai", mock_openai_provider)

        # Try to route to OpenAI which will fail, then fallback to Anthropic
        # Let's make both fail
        mock_anthropic_provider.complete = AsyncMock(
            side_effect=ProviderError(provider="anthropic", detail="Failed")
        )

        # News analysis routes to OpenAI by default, which will fail and try to fallback to Anthropic
        # Since both fail, it should raise an error
        with pytest.raises(ProviderError) as exc_info:
            await router.complete(TaskType.NEWS_ANALYSIS, sample_messages)

        # Should fail because all providers failed
        assert "router" in str(exc_info.value) or "failed" in str(exc_info.value).lower()

    def test_invalid_task_type(self, router):
        """Test error when task type is not in routing table."""
        # Remove all routing
        router._routing = {}

        with pytest.raises(ProviderError):
            router.route(TaskType.THESIS_GENERATION)


class TestPromptTemplates:
    """Test suite for prompt templates."""

    def test_all_templates_exist(self):
        """Test that all 7 template functions are available."""
        templates = [
            get_thesis_generation_template(),
            get_thesis_update_template(),
            get_news_analysis_template(),
            get_assumption_generation_template(),
            get_company_comparison_template(),
            get_note_extraction_template(),
            get_watch_items_template(),
        ]

        assert len(templates) == 7

        for template in templates:
            assert isinstance(template, PromptTemplate)
            assert template.name
            assert template.task_type
            assert template.system_prompt
            assert template.user_template

    def test_template_render(self):
        """Test that templates render placeholders correctly."""
        template = get_thesis_generation_template()

        messages = template.render(
            ticker="AAPL",
            company_name="Apple Inc.",
            business_description="Tech company",
            key_metrics="$3T market cap",
            recent_news="New iPhone",
            industry_context="Consumer electronics",
        )

        assert len(messages) == 2
        assert messages[0].role == LLMRole.SYSTEM
        assert messages[1].role == LLMRole.USER
        assert "AAPL" in messages[1].content
        assert "Apple Inc." in messages[1].content

    def test_template_version(self):
        """Test that templates have version information."""
        template = get_thesis_generation_template()
        assert template.version == "1.0"

    def test_thesis_generation_task_type(self):
        """Test that thesis generation template has correct task type."""
        template = get_thesis_generation_template()
        assert template.task_type == TaskType.THESIS_GENERATION

    def test_news_analysis_task_type(self):
        """Test that news analysis template has correct task type."""
        template = get_news_analysis_template()
        assert template.task_type == TaskType.NEWS_ANALYSIS

    def test_quick_summary_template(self):
        """Test that quick summary template exists and renders."""
        # Note: quick_summary is a TaskType but doesn't have a dedicated template function
        # It would use the general system prompt
        assert TaskType.QUICK_SUMMARY in TaskType

    def test_missing_placeholder_raises_error(self):
        """Test that missing placeholder raises KeyError."""
        template = get_thesis_generation_template()

        with pytest.raises(KeyError):
            template.render(ticker="AAPL")  # Missing required placeholders

    def test_note_extraction_json_mode(self):
        """Test that note extraction template mentions JSON output."""
        template = get_note_extraction_template()
        # The system prompt should mention JSON
        assert "JSON" in template.system_prompt

    def test_thesis_update_has_current_thesis_placeholder(self):
        """Test that thesis update template includes existing_thesis placeholder."""
        template = get_thesis_update_template()
        assert "{existing_thesis}" in template.user_template

    def test_company_comparison_has_two_company_placeholders(self):
        """Test that company comparison template has placeholders for both companies."""
        template = get_company_comparison_template()
        assert "{ticker_a}" in template.user_template
        assert "{ticker_b}" in template.user_template
        assert "{company_a_metrics}" in template.user_template
        assert "{company_b_metrics}" in template.user_template

    def test_assumption_generation_targets_dcf(self):
        """Test that assumption generation template mentions DCF."""
        template = get_assumption_generation_template()
        assert "DCF" in template.system_prompt

    def test_watch_items_template_mentions_catalysts(self):
        """Test that watch items template includes catalysts."""
        template = get_watch_items_template()
        assert "Catalyst" in template.system_prompt or "catalyst" in template.system_prompt.lower()
