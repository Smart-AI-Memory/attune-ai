"""Tests for LLM provider classes (Claude-native).

Comprehensive test coverage for Anthropic provider classes.

Created: 2026-01-20
Coverage target: 80%+
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.llm.providers import (
    AnthropicBatchProvider,
    AnthropicProvider,
    BaseLLMProvider,
    LLMResponse,
)

# =============================================================================
# LLMResponse Tests
# =============================================================================


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_creation(self):
        """Test creating an LLMResponse."""
        response = LLMResponse(
            content="Hello world",
            model="claude-3-sonnet",
            tokens_used=100,
            finish_reason="stop",
            metadata={"provider": "anthropic"},
        )

        assert response.content == "Hello world"
        assert response.model == "claude-3-sonnet"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
        assert response.metadata["provider"] == "anthropic"


# =============================================================================
# BaseLLMProvider Tests
# =============================================================================


class TestBaseLLMProvider:
    """Tests for BaseLLMProvider base class."""

    def test_init(self):
        """Test initialization stores api_key and config."""

        # Create concrete implementation
        class ConcreteProvider(BaseLLMProvider):
            async def generate(self, messages, **kwargs):
                return LLMResponse("", "", 0, "", {})

            def get_model_info(self):
                return {}

        provider = ConcreteProvider(api_key="test-key", custom_option=True)

        assert provider.api_key == "test-key"
        assert provider.config["custom_option"] is True

    def test_estimate_tokens(self):
        """Test token estimation."""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(self, messages, **kwargs):
                return LLMResponse("", "", 0, "", {})

            def get_model_info(self):
                return {}

        provider = ConcreteProvider()

        # Rough approximation: ~4 chars per token
        assert provider.estimate_tokens("Hello world!") == 3  # 12 chars / 4
        assert provider.estimate_tokens("A" * 400) == 100


# =============================================================================
# AnthropicProvider Tests
# =============================================================================


class TestAnthropicProvider:
    """Tests for AnthropicProvider class."""

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicProvider(api_key=None)

        with pytest.raises(ValueError, match="API key is required"):
            AnthropicProvider(api_key="")

        with pytest.raises(ValueError, match="API key is required"):
            AnthropicProvider(api_key="   ")

    def test_init_requires_anthropic_package(self):
        """Test handling when anthropic package not installed."""
        with (
            patch.dict("sys.modules", {"anthropic": None}),
            patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'anthropic'"),
            ),
            pytest.raises(ImportError, match="anthropic package required"),
        ):
            AnthropicProvider(api_key="sk-test")

    @patch("anthropic.AsyncAnthropic")
    def test_init_success(self, mock_anthropic_class):
        """Test successful initialization."""
        provider = AnthropicProvider(
            api_key="sk-test",
            model="claude-3-sonnet",
            use_prompt_caching=True,
        )

        assert provider.model == "claude-3-sonnet"
        assert provider.use_prompt_caching is True
        assert provider.api_key == "sk-test"

    @patch("anthropic.Anthropic")
    @patch("anthropic.AsyncAnthropic")
    def test_init_with_batch(self, mock_async_class, mock_sync_class):
        """Test initialization with batch provider."""
        provider = AnthropicProvider(
            api_key="sk-test",
            use_batch=True,
        )

        assert provider.batch_provider is not None

    @patch("anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_generate_basic(self, mock_anthropic_class):
        """Test basic generation."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.model = "claude-3-sonnet"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicProvider(api_key="sk-test")

        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result.content == "Hello!"
        assert result.tokens_used == 15
        assert result.metadata["provider"] == "anthropic"

    @patch("anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt_caching(self, mock_anthropic_class):
        """Test generation with prompt caching enabled."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Response")]
        mock_response.model = "claude-3-sonnet"
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=80,
            cache_read_input_tokens=0,
        )
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicProvider(api_key="sk-test", use_prompt_caching=True)

        result = await provider.generate(
            messages=[{"role": "user", "content": "Test"}],
            system_prompt="You are a helpful assistant",
        )

        # Verify cache_control was added
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert isinstance(call_kwargs["system"], list)
        assert call_kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}

        # Verify cache metrics in metadata
        assert result.metadata["cache_creation_tokens"] == 80

    @patch("anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_generate_with_thinking(self, mock_anthropic_class):
        """Test generation with thinking mode enabled."""
        mock_response = MagicMock()
        mock_thinking_block = MagicMock()
        mock_thinking_block.type = "thinking"
        mock_thinking_block.thinking = "Let me think..."
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Final answer"
        mock_response.content = [mock_thinking_block, mock_text_block]
        mock_response.model = "claude-3-sonnet"
        mock_response.usage = MagicMock(input_tokens=20, output_tokens=30)
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicProvider(
            api_key="sk-test", use_thinking=True, model="claude-sonnet-4-5"
        )

        result = await provider.generate(
            messages=[{"role": "user", "content": "Complex question"}],
        )

        # Verify thinking was requested
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "thinking" in call_kwargs

        # Verify thinking content in metadata
        assert result.metadata["thinking"] == "Let me think..."
        assert result.content == "Final answer"

    @patch("anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_thinking_grows_max_tokens_above_budget(self, mock_anthropic_class):
        """Regression: thinking with max_tokens <= budget_tokens must not 400.

        The API requires max_tokens > thinking.budget_tokens (thinking
        output counts toward max_tokens). The provider must grow
        max_tokens — never shrink the configured budget — and force
        temperature=1.0 (thinking rejects any other value).
        """
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "ok"
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicProvider(
            api_key="sk-test", use_thinking=True, model="claude-sonnet-4-5"
        )

        # Default thinking_budget=10000, max_tokens=2048 — the exact shape
        # that 400'd in the nightly integration-auth run.
        await provider.generate(
            messages=[{"role": "user", "content": "Q"}],
            temperature=0.7,
            max_tokens=2048,
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 10000}
        assert call_kwargs["max_tokens"] > 10000
        assert call_kwargs["extra_body"]["temperature"] == 1.0

    @patch("anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_thinking_keeps_max_tokens_when_already_large_enough(self, mock_anthropic_class):
        """A max_tokens already above the budget is passed through unchanged."""
        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "ok"
        mock_response.content = [mock_block]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicProvider(
            api_key="sk-test", use_thinking=True, thinking_budget=2000, model="claude-sonnet-4-5"
        )

        await provider.generate(
            messages=[{"role": "user", "content": "Q"}],
            max_tokens=8192,
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 8192
        assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 2000}

    @patch("anthropic.AsyncAnthropic")
    def test_get_model_info_known_model(self, mock_anthropic_class):
        """Test getting model info for known model."""
        provider = AnthropicProvider(
            api_key="sk-test",
            model="claude-3-5-sonnet-20241022",
        )

        info = provider.get_model_info()

        assert info["max_tokens"] == 200000
        assert info["supports_prompt_caching"] is True

    @patch("anthropic.AsyncAnthropic")
    def test_get_model_info_unknown_model(self, mock_anthropic_class):
        """Test getting model info for unknown model."""
        provider = AnthropicProvider(
            api_key="sk-test",
            model="claude-unknown",
        )

        info = provider.get_model_info()

        # Should return default values
        assert info["max_tokens"] == 200000


# =============================================================================
# AnthropicBatchProvider Tests
# =============================================================================


class TestAnthropicBatchProvider:
    """Tests for AnthropicBatchProvider class."""

    @pytest.fixture
    def mock_anthropic_class(self):
        """Patch anthropic.Anthropic for batch provider tests."""
        with patch("anthropic.Anthropic") as mock_cls:
            yield mock_cls

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicBatchProvider(api_key=None)

    def test_create_batch_empty_requests(self, mock_anthropic_class):
        """Test creating batch with empty requests."""
        provider = AnthropicBatchProvider(api_key="sk-test")

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.create_batch([])

    def test_create_batch_success(self, mock_anthropic_class):
        """Test successful batch creation."""
        mock_batch = MagicMock()
        mock_batch.id = "batch_123"

        mock_client = MagicMock()
        mock_client.messages.batches.create.return_value = mock_batch
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicBatchProvider(api_key="sk-test")

        requests = [
            {
                "custom_id": "task_1",
                "model": "claude-sonnet-5",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 100,
            },
        ]

        batch_id = provider.create_batch(requests)

        assert batch_id == "batch_123"

    def test_get_batch_status(self, mock_anthropic_class):
        """Test getting batch status."""
        mock_batch = MagicMock()
        mock_batch.processing_status = "in_progress"

        mock_client = MagicMock()
        mock_client.messages.batches.retrieve.return_value = mock_batch
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicBatchProvider(api_key="sk-test")

        status = provider.get_batch_status("batch_123")

        assert status.processing_status == "in_progress"

    def test_get_batch_results_not_completed(self, mock_anthropic_class):
        """Test getting results when batch not completed."""
        mock_batch = MagicMock()
        mock_batch.processing_status = "in_progress"

        mock_client = MagicMock()
        mock_client.messages.batches.retrieve.return_value = mock_batch
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicBatchProvider(api_key="sk-test")

        with pytest.raises(ValueError, match="not ended"):
            provider.get_batch_results("batch_123")

    def test_get_batch_results_success(self, mock_anthropic_class):
        """Test getting results from completed batch."""
        mock_batch = MagicMock()
        mock_batch.processing_status = "ended"

        mock_results = [{"custom_id": "task_1", "response": {"content": "Result"}}]

        mock_client = MagicMock()
        mock_client.messages.batches.retrieve.return_value = mock_batch
        mock_client.messages.batches.results.return_value = iter(mock_results)
        mock_anthropic_class.return_value = mock_client

        provider = AnthropicBatchProvider(api_key="sk-test")

        results = provider.get_batch_results("batch_123")

        assert len(results) == 1
        assert results[0]["custom_id"] == "task_1"


# =============================================================================
# Integration Tests
# =============================================================================


class TestProviderSelection:
    """Tests for provider selection patterns."""

    def test_anthropic_has_required_methods(self):
        """Verify AnthropicProvider implements required abstract methods."""
        assert hasattr(AnthropicProvider, "generate")
        assert hasattr(AnthropicProvider, "get_model_info")
        assert hasattr(AnthropicProvider, "estimate_tokens")

    def test_llm_response_is_compatible(self):
        """Verify LLMResponse format works correctly."""
        response = LLMResponse(
            content="Test",
            model="any-model",
            tokens_used=100,
            finish_reason="stop",
            metadata={"provider": "test"},
        )

        assert response.content == "Test"
        assert response.model == "any-model"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
        assert response.metadata["provider"] == "test"
