"""Tests for empathy_llm_toolkit providers module.

Comprehensive test coverage for LLM provider classes.

Created: 2026-01-20
Coverage target: 80%+
"""

import importlib.util
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Check for optional dependencies
_openai_available = importlib.util.find_spec("openai") is not None
_aiohttp_available = importlib.util.find_spec("aiohttp") is not None

from attune_llm.providers import (  # noqa: E402
    AnthropicBatchProvider,
    AnthropicProvider,
    BaseLLMProvider,
    GeminiProvider,
    LLMResponse,
    LocalProvider,
    OpenAIProvider,
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
        with patch.dict("sys.modules", {"anthropic": None}):
            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'anthropic'")
            ):
                with pytest.raises(ImportError, match="anthropic package required"):
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

    @patch("anthropic.AsyncAnthropic")
    def test_init_with_batch(self, mock_anthropic_class):
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

        provider = AnthropicProvider(api_key="sk-test", use_thinking=True)

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

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicBatchProvider(api_key=None)

    @patch("anthropic.Anthropic")
    def test_create_batch_empty_requests(self, mock_anthropic_class):
        """Test creating batch with empty requests."""
        provider = AnthropicBatchProvider(api_key="sk-test")

        with pytest.raises(ValueError, match="cannot be empty"):
            provider.create_batch([])

    @patch("anthropic.Anthropic")
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
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 100,
            }
        ]

        batch_id = provider.create_batch(requests)

        assert batch_id == "batch_123"

    @patch("anthropic.Anthropic")
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

    @patch("anthropic.Anthropic")
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

    @patch("anthropic.Anthropic")
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
# OpenAIProvider Tests
# =============================================================================


@pytest.mark.skipif(
    not _openai_available,
    reason="openai not installed (optional dependency)",
)
class TestOpenAIProvider:
    """Tests for OpenAIProvider class."""

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            OpenAIProvider(api_key=None)

    def test_init_requires_openai_package(self):
        """Test handling when openai package not installed."""
        with patch.dict("sys.modules", {"openai": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ImportError, match="openai package required"):
                    OpenAIProvider(api_key="sk-test")

    @patch("openai.AsyncOpenAI")
    def test_init_success(self, mock_openai_class):
        """Test successful initialization."""
        provider = OpenAIProvider(
            api_key="sk-test",
            model="gpt-4",
        )

        assert provider.model == "gpt-4"
        assert provider.api_key == "sk-test"

    @patch("openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_generate(self, mock_openai_class):
        """Test generation with OpenAI."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello from GPT!"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = MagicMock(
            total_tokens=50,
            prompt_tokens=20,
            completion_tokens=30,
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(api_key="sk-test")

        result = await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result.content == "Hello from GPT!"
        assert result.tokens_used == 50
        assert result.metadata["provider"] == "openai"

    @patch("openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, mock_openai_class):
        """Test generation with system prompt."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Response"
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4"
        mock_response.usage = MagicMock(total_tokens=30, prompt_tokens=20, completion_tokens=10)

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(api_key="sk-test")

        await provider.generate(
            messages=[{"role": "user", "content": "Hi"}],
            system_prompt="Be helpful",
        )

        # Verify system message was prepended
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][0]["content"] == "Be helpful"

    @patch("openai.AsyncOpenAI")
    def test_get_model_info_known(self, mock_openai_class):
        """Test getting model info for known model."""
        provider = OpenAIProvider(api_key="sk-test", model="gpt-4")

        info = provider.get_model_info()

        assert info["max_tokens"] == 8192

    @patch("openai.AsyncOpenAI")
    def test_get_model_info_unknown(self, mock_openai_class):
        """Test getting model info for unknown model."""
        provider = OpenAIProvider(api_key="sk-test", model="gpt-unknown")

        info = provider.get_model_info()

        # Should return default
        assert "max_tokens" in info


# =============================================================================
# GeminiProvider Tests
# =============================================================================


class TestGeminiProvider:
    """Tests for GeminiProvider class."""

    def test_init_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError, match="API key is required"):
            GeminiProvider(api_key=None)

    def test_init_requires_google_package(self):
        """Test handling when google-generativeai package not installed."""

        # Create mock that raises ImportError
        def mock_import(name, *args, **kwargs):
            if "google" in name:
                raise ImportError("No module named 'google.generativeai'")
            return original_import(name, *args, **kwargs)

        import builtins

        original_import = builtins.__import__

        with patch.object(builtins, "__import__", side_effect=mock_import):
            with pytest.raises(ImportError, match="google-generativeai package required"):
                # Need to reimport the module to trigger the import error
                import importlib

                import attune_llm.providers as providers_mod

                importlib.reload(providers_mod)
                providers_mod.GeminiProvider(api_key="test-key")

    def test_init_success(self):
        """Test successful initialization with mocked genai."""
        mock_genai = MagicMock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            # Need to reimport to use mocked module
            from attune_llm.providers import GeminiProvider as GP

            provider = GP.__new__(GP)
            provider.api_key = "test-key"
            provider.model = "gemini-1.5-pro"
            provider.config = {}
            provider.genai = mock_genai
            provider.client = mock_model

            assert provider.model == "gemini-1.5-pro"

    def test_get_tier_cheap(self):
        """Test tier detection for cheap models."""
        # Create provider without full init
        provider = object.__new__(GeminiProvider)
        provider.model = "gemini-2.0-flash-exp"

        assert provider._get_tier() == "cheap"

    def test_get_tier_premium(self):
        """Test tier detection for premium models."""
        provider = object.__new__(GeminiProvider)
        provider.model = "gemini-2.5-pro"

        assert provider._get_tier() == "premium"

    def test_get_tier_capable(self):
        """Test tier detection for capable models."""
        provider = object.__new__(GeminiProvider)
        provider.model = "gemini-1.5-pro"

        assert provider._get_tier() == "capable"

    def test_get_model_info_known(self):
        """Test getting model info for known model."""
        provider = object.__new__(GeminiProvider)
        provider.model = "gemini-1.5-pro"

        info = provider.get_model_info()

        assert info["max_tokens"] == 2000000
        assert info["supports_vision"] is True

    def test_get_model_info_unknown(self):
        """Test getting model info for unknown model."""
        provider = object.__new__(GeminiProvider)
        provider.model = "gemini-unknown"

        info = provider.get_model_info()

        # Should return default
        assert "max_tokens" in info


# =============================================================================
# LocalProvider Tests
# =============================================================================


@pytest.mark.skipif(
    not _aiohttp_available,
    reason="aiohttp not installed (optional dependency)",
)
class TestLocalProvider:
    """Tests for LocalProvider class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        provider = LocalProvider()

        assert provider.endpoint == "http://localhost:11434"
        assert provider.model == "llama2"
        assert provider.api_key is None

    def test_init_custom(self):
        """Test initialization with custom values."""
        provider = LocalProvider(
            endpoint="http://localhost:8080",
            model="codellama",
        )

        assert provider.endpoint == "http://localhost:8080"
        assert provider.model == "codellama"

    @pytest.mark.asyncio
    async def test_generate(self):
        """Test generation with local model."""
        provider = LocalProvider()

        mock_response = MagicMock()
        mock_response.json = AsyncMock(
            return_value={
                "message": {"content": "Hello from local!"},
                "eval_count": 30,
                "prompt_eval_count": 10,
            }
        )

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock(),
            )
        )

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client_session.return_value.__aexit__ = AsyncMock()

            result = await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
            )

            assert result.content == "Hello from local!"
            assert result.tokens_used == 40
            assert result.metadata["provider"] == "local"

    def test_get_model_info(self):
        """Test getting model info for local provider."""
        provider = LocalProvider()

        info = provider.get_model_info()

        assert info["max_tokens"] == 4096
        assert info["cost_per_1m_input"] == 0.0  # Free
        assert info["endpoint"] == "http://localhost:11434"


# =============================================================================
# Integration Tests
# =============================================================================


class TestProviderSelection:
    """Tests for provider selection patterns."""

    def test_all_providers_have_required_methods(self):
        """Verify all providers implement required abstract methods."""
        providers = [
            # Can't instantiate without mocking, but can check class methods
            AnthropicProvider,
            OpenAIProvider,
            GeminiProvider,
            LocalProvider,
        ]

        for provider_class in providers:
            assert hasattr(provider_class, "generate")
            assert hasattr(provider_class, "get_model_info")
            assert hasattr(provider_class, "estimate_tokens")

    def test_llm_response_is_compatible_across_providers(self):
        """Verify all responses use the same LLMResponse format."""
        # Create sample response
        response = LLMResponse(
            content="Test",
            model="any-model",
            tokens_used=100,
            finish_reason="stop",
            metadata={"provider": "test"},
        )

        # All fields should be accessible
        assert response.content == "Test"
        assert response.model == "any-model"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
        assert response.metadata["provider"] == "test"
