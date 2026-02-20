"""Tests for LLM providers (OpenAI and Anthropic)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.core.errors import ProviderError, RateLimitError
from app.services.llm.providers.anthropic_provider import AnthropicProvider
from app.services.llm.providers.openai_provider import OpenAIProvider
from app.services.llm.types import LLMMessage, LLMRole


@pytest.fixture
def mock_http_request():
    """Create a mock httpx.Request object."""
    request = Mock()
    request.url = "https://api.example.com/v1/chat/completions"
    request.method = "POST"
    return request


@pytest.fixture
def mock_http_response(mock_http_request):
    """Create a mock httpx.Response object."""
    response = Mock()
    response.request = mock_http_request
    response.status_code = 429
    return response


class TestOpenAIProvider:
    """Test suite for OpenAI provider."""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create a provider instance with mock API key."""
        return OpenAIProvider(api_key="test-api-key")

    @pytest.fixture
    def sample_messages(self) -> list[LLMMessage]:
        """Sample messages for testing."""
        return [
            LLMMessage(role=LLMRole.SYSTEM, content="You are a helpful assistant."),
            LLMMessage(role=LLMRole.USER, content="What is the capital of France?"),
        ]

    @pytest.mark.asyncio
    async def test_complete_success(self, provider, sample_messages):
        """Test successful completion returns correct LLMResponse."""
        # Mock the OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The capital of France is Paris."
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 10

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages)

        assert response.content == "The capital of France is Paris."
        assert response.model == "gpt-4o"  # Default model
        assert response.provider == "openai"
        assert response.input_tokens == 20
        assert response.output_tokens == 10
        assert response.finish_reason == "stop"
        assert response.latency_ms > 0
        assert response.cost_usd is not None

    @pytest.mark.asyncio
    async def test_complete_json_mode(self, provider, sample_messages):
        """Test that json_mode sets response_format correctly."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"answer": "Paris"}'
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 5

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        await provider.complete(sample_messages, json_mode=True)

        # Verify response_format was set
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_token_tracking(self, provider, sample_messages):
        """Test that input and output tokens are tracked correctly."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages)

        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.input_tokens + response.output_tokens == 150

    @pytest.mark.asyncio
    async def test_cost_calculation(self, provider, sample_messages):
        """Test that cost is calculated correctly from pricing dict."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 1_000_000  # 1M input tokens
        mock_response.usage.completion_tokens = 1_000_000  # 1M output tokens

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages, model="gpt-4o")

        # gpt-4o: $2.50 input, $10.00 output per 1M tokens
        expected_cost = 2.50 + 10.00
        assert response.cost_usd == expected_cost

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, provider, sample_messages, mock_http_response):
        """Test that rate limit errors are wrapped correctly."""
        from openai import RateLimitError as OpenAIRateLimitError

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIRateLimitError(message="Rate limit exceeded", response=mock_http_response, body=None)
        )

        provider._client = mock_client

        with pytest.raises(RateLimitError) as exc_info:
            await provider.complete(sample_messages)

        assert "openai" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_provider_error(self, provider, sample_messages, mock_http_request):
        """Test that API errors are wrapped in ProviderError."""
        from openai import APIError as OpenAIError

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=OpenAIError(message="API error", request=mock_http_request, body=None)
        )

        provider._client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await provider.complete(sample_messages)

        assert "openai" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_complete_stream(self, provider, sample_messages):
        """Test streaming yields chunks correctly."""
        chunks_result = ["The ", "capital ", "of ", "France ", "is ", "Paris."]

        # Create a mock async generator
        async def mock_stream():
            for chunk in chunks_result:
                mock_chunk = MagicMock()
                mock_chunk.choices = [MagicMock()]
                mock_chunk.choices[0].delta.content = chunk
                yield mock_chunk

        # Create a mock that returns an async generator when called
        async def create_mock_stream(**kwargs):
            return mock_stream()

        mock_client = AsyncMock()
        mock_client.chat.completions.create = create_mock_stream

        provider._client = mock_client

        chunks = []
        async for chunk in provider.complete_stream(sample_messages):
            chunks.append(chunk)

        assert "".join(chunks) == "The capital of France is Paris."

    @pytest.mark.asyncio
    async def test_custom_model(self, provider, sample_messages):
        """Test using a custom model."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages, model="gpt-4o-mini")

        assert response.model == "gpt-4o-mini"
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"


class TestAnthropicProvider:
    """Test suite for Anthropic provider."""

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create a provider instance with mock API key."""
        return AnthropicProvider(api_key="test-api-key")

    @pytest.fixture
    def sample_messages(self) -> list[LLMMessage]:
        """Sample messages for testing."""
        return [
            LLMMessage(role=LLMRole.SYSTEM, content="You are a helpful assistant."),
            LLMMessage(role=LLMRole.USER, content="What is the capital of France?"),
        ]

    @pytest.mark.asyncio
    async def test_complete_success(self, provider, sample_messages):
        """Test successful completion returns correct LLMResponse."""
        # Mock the Anthropic client response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "The capital of France is Paris."
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 25
        mock_response.usage.output_tokens = 10

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages)

        assert response.content == "The capital of France is Paris."
        assert response.model == "claude-sonnet-4-20250514"  # Default model
        assert response.provider == "anthropic"
        assert response.input_tokens == 25
        assert response.output_tokens == 10
        assert response.finish_reason == "end_turn"
        assert response.latency_ms > 0
        assert response.cost_usd is not None

    @pytest.mark.asyncio
    async def test_system_message_extraction(self, provider, sample_messages):
        """Test that system messages are extracted and passed separately."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response"
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 30
        mock_response.usage.output_tokens = 5

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        await provider.complete(sample_messages)

        # Verify system parameter was set correctly
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["system"] == "You are a helpful assistant.\n\n"
        # And that system message is NOT in messages list
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_multiple_system_messages(self, provider):
        """Test that multiple system messages are combined."""
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="First system message."),
            LLMMessage(role=LLMRole.SYSTEM, content="Second system message."),
            LLMMessage(role=LLMRole.USER, content="User question"),
        ]

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response"
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 10

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        await provider.complete(messages)

        call_args = mock_client.messages.create.call_args
        system = call_args.kwargs["system"]
        assert "First system message." in system
        assert "Second system message." in system

    @pytest.mark.asyncio
    async def test_token_tracking(self, provider, sample_messages):
        """Test that token counts are tracked correctly."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response"
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 100

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages)

        assert response.input_tokens == 200
        assert response.output_tokens == 100

    @pytest.mark.asyncio
    async def test_cost_calculation(self, provider, sample_messages):
        """Test that cost is calculated correctly."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Response"
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 1_000_000
        mock_response.usage.output_tokens = 1_000_000

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        provider._client = mock_client

        response = await provider.complete(sample_messages)

        # Claude Sonnet 4: $3.00 input, $15.00 output per 1M tokens
        expected_cost = 3.00 + 15.00
        assert response.cost_usd == expected_cost

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, provider, sample_messages, mock_http_response):
        """Test that rate limit errors are wrapped correctly."""
        from anthropic import RateLimitError as AnthropicRateLimitError

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=AnthropicRateLimitError(message="Rate limit", response=mock_http_response, body=None)
        )

        provider._client = mock_client

        with pytest.raises(RateLimitError) as exc_info:
            await provider.complete(sample_messages)

        assert "anthropic" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_provider_error(self, provider, sample_messages, mock_http_request):
        """Test that API errors are wrapped in ProviderError."""
        from anthropic import APIError as AnthropicError

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=AnthropicError(message="API error", request=mock_http_request, body=None)
        )

        provider._client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await provider.complete(sample_messages)

        assert "anthropic" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_complete_stream(self, provider, sample_messages):
        """Test streaming yields chunks correctly."""
        # Create mock text stream
        async def mock_text_stream():
            """Mock streaming text."""
            yield "The "
            yield "capital "
            yield "of "
            yield "France "
            yield "is "
            yield "Paris."

        # Create a proper async context manager mock
        class MockStreamContext:
            def __init__(self):
                self._text_stream = mock_text_stream()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            @property
            def text_stream(self):
                return self._text_stream

        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=MockStreamContext())

        provider._client = mock_client

        chunks = []
        async for chunk in provider.complete_stream(sample_messages):
            chunks.append(chunk)

        assert "".join(chunks) == "The capital of France is Paris."
