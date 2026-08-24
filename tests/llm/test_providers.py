"""Comprehensive tests for LLM Provider Adapters

Tests cover:
- LLMResponse dataclass
- BaseLLMProvider abstract class and methods
- AnthropicProvider initialization and validation
- Provider factory patterns
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.llm.providers import (
    AnthropicProvider,
    BaseLLMProvider,
    LLMResponse,
)


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_llm_response_creation(self):
        """Test LLMResponse dataclass creation"""
        response = LLMResponse(
            content="Test response",
            model="claude-3-sonnet",
            tokens_used=150,
            finish_reason="stop",
            metadata={"input_tokens": 100, "output_tokens": 50},
        )

        assert response.content == "Test response"
        assert response.model == "claude-3-sonnet"
        assert response.tokens_used == 150
        assert response.finish_reason == "stop"
        assert response.metadata["input_tokens"] == 100
        assert response.metadata["output_tokens"] == 50

    def test_llm_response_with_empty_metadata(self):
        """Test LLMResponse with empty metadata"""
        response = LLMResponse(
            content="Hello",
            model="gpt-4",
            tokens_used=10,
            finish_reason="stop",
            metadata={},
        )

        assert response.content == "Hello"
        assert response.metadata == {}


class TestBaseLLMProvider:
    """Test BaseLLMProvider abstract base class"""

    def test_base_provider_initialization(self):
        """Test BaseLLMProvider can be initialized with api_key and kwargs"""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(
                self,
                messages,
                system_prompt=None,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            ):
                return LLMResponse("test", "model", 10, "stop", {})

            def get_model_info(self):
                return {"model": "test"}

        provider = ConcreteProvider(api_key="test-key", custom_param="value")

        assert provider.api_key == "test-key"
        assert provider.config["custom_param"] == "value"

    def test_base_provider_no_api_key(self):
        """Test BaseLLMProvider can be initialized without api_key"""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(
                self,
                messages,
                system_prompt=None,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            ):
                return LLMResponse("test", "model", 10, "stop", {})

            def get_model_info(self):
                return {"model": "test"}

        provider = ConcreteProvider()
        assert provider.api_key is None

    def test_estimate_tokens_short_text(self):
        """Test token estimation for short text"""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(
                self,
                messages,
                system_prompt=None,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            ):
                return LLMResponse("test", "model", 10, "stop", {})

            def get_model_info(self):
                return {"model": "test"}

        provider = ConcreteProvider()
        text = "Hello world"  # 11 characters
        tokens = provider.estimate_tokens(text)

        assert tokens == 2  # 11 // 4 = 2

    def test_estimate_tokens_long_text(self):
        """Test token estimation for longer text"""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(
                self,
                messages,
                system_prompt=None,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            ):
                return LLMResponse("test", "model", 10, "stop", {})

            def get_model_info(self):
                return {"model": "test"}

        provider = ConcreteProvider()
        text = "a" * 400  # 400 characters
        tokens = provider.estimate_tokens(text)

        assert tokens == 100  # 400 // 4 = 100

    def test_estimate_tokens_empty_text(self):
        """Test token estimation for empty text"""

        class ConcreteProvider(BaseLLMProvider):
            async def generate(
                self,
                messages,
                system_prompt=None,
                temperature=0.7,
                max_tokens=1024,
                **kwargs,
            ):
                return LLMResponse("test", "model", 10, "stop", {})

            def get_model_info(self):
                return {"model": "test"}

        provider = ConcreteProvider()
        tokens = provider.estimate_tokens("")

        assert tokens == 0


class TestAnthropicProvider:
    """Test Anthropic provider initialization and validation"""

    def test_anthropic_provider_requires_api_key(self):
        """Test that AnthropicProvider requires API key"""
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicProvider(api_key=None)

    def test_anthropic_provider_requires_non_empty_api_key(self):
        """Test that AnthropicProvider requires non-empty API key"""
        with pytest.raises(ValueError, match="API key is required"):
            AnthropicProvider(api_key="   ")

    def test_anthropic_provider_missing_package(self):
        """Test error when anthropic package not installed"""
        with patch("builtins.__import__", side_effect=ImportError):
            with pytest.raises(ImportError, match="anthropic package required"):
                AnthropicProvider(api_key="test-key")

    def test_anthropic_provider_initialization_success(self):
        """Test successful AnthropicProvider initialization"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(
                api_key="test-key",
                model="claude-3-opus",
                use_prompt_caching=True,
                use_thinking=True,
            )

            assert provider.api_key == "test-key"
            assert provider.model == "claude-3-opus"
            assert provider.use_prompt_caching is True
            assert provider.use_thinking is True

    def test_anthropic_provider_default_model(self):
        """Test AnthropicProvider default model"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")

            assert provider.model == "claude-sonnet-5"

    def test_anthropic_get_model_info_opus(self):
        """Test get_model_info for Claude Opus"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", model="claude-3-opus-20240229")

            info = provider.get_model_info()

            assert info["max_tokens"] == 200000
            assert info["supports_prompt_caching"] is True
            assert info["supports_thinking"] is True
            assert "ideal_for" in info

    def test_anthropic_get_model_info_unknown_model(self):
        """Test get_model_info for unknown model returns defaults"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", model="unknown-model")

            info = provider.get_model_info()

            assert info["max_tokens"] == 200000
            assert info["supports_prompt_caching"] is True


class TestProviderComparison:
    """Test provider class hierarchy"""

    def test_anthropic_implements_base_interface(self):
        """Test that AnthropicProvider implements required abstract methods."""
        assert issubclass(AnthropicProvider, BaseLLMProvider)

    def test_anthropic_has_get_model_info(self):
        """Test AnthropicProvider implements get_model_info."""
        mock_anthropic = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            anthropic = AnthropicProvider(api_key="key1")

            assert hasattr(anthropic, "get_model_info")
            assert isinstance(anthropic.get_model_info(), dict)


class TestAnthropicProviderGenerate:
    """Test Anthropic provider generate method and response handling"""

    @pytest.mark.asyncio
    async def test_anthropic_generate_basic(self):
        """Test basic Anthropic generate call"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        # Mock content block (text type)
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Test response"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages)

            assert result.content == "Test response"
            assert result.model == "claude-3-sonnet"
            assert result.tokens_used == 150
            assert result.finish_reason == "end_turn"
            assert result.metadata["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_system_prompt_and_caching(self):
        """Test Anthropic generate with system prompt and prompt caching"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.usage.cache_creation_input_tokens = 200
        mock_response.usage.cache_read_input_tokens = 150

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Cached response"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages, system_prompt="You are helpful")

            assert result.content == "Cached response"
            assert result.metadata["cache_creation_tokens"] == 200
            assert result.metadata["cache_read_tokens"] == 150

    @pytest.mark.asyncio
    async def test_anthropic_generate_without_caching(self):
        """Test Anthropic generate with system prompt but no caching"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Regular response"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_prompt_caching=False)

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages, system_prompt="You are helpful")

            assert result.content == "Regular response"

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_thinking_mode(self):
        """Test Anthropic generate with thinking mode enabled"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        # Mock thinking block
        mock_thinking_block = MagicMock()
        mock_thinking_block.type = "thinking"
        mock_thinking_block.thinking = "Let me think about this..."

        # Mock text block
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Based on my thinking..."

        mock_response.content = [mock_thinking_block, mock_text_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_thinking=True)

            messages = [{"role": "user", "content": "Complex question"}]
            result = await provider.generate(messages)

            assert result.content == "Based on my thinking..."
            assert result.metadata["thinking"] == "Let me think about this..."

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_legacy_content_block(self):
        """Test Anthropic generate with content block without type attribute"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        # Mock content block without type attribute (legacy format)
        mock_block = MagicMock()
        del mock_block.type  # Remove type attribute
        mock_block.text = "Legacy response"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages)

            assert result.content == "Legacy response"

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_unknown_block_type(self):
        """Test Anthropic generate with unknown block type (skip it)"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        # Mock block with unknown type
        mock_unknown_block = MagicMock()
        mock_unknown_block.type = "unknown_type"

        # Mock text block
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Text response"

        mock_response.content = [mock_unknown_block, mock_text_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages)

            # Should get text from the text block, unknown block skipped
            assert result.content == "Text response"

    @pytest.mark.asyncio
    async def test_anthropic_generate_without_cache_metrics(self):
        """Test Anthropic generate without cache metrics in response"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"

        # Create usage object without cache attributes
        mock_usage = type("obj", (object,), {"input_tokens": 100, "output_tokens": 50})()
        mock_response.usage = mock_usage

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Response without cache"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_prompt_caching=True)

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages, system_prompt="You are helpful")

            assert result.content == "Response without cache"
            # Should not have cache metrics
            assert "cache_creation_tokens" not in result.metadata
            assert "cache_read_tokens" not in result.metadata

    @pytest.mark.asyncio
    async def test_anthropic_generate_without_thinking_content(self):
        """Test Anthropic generate without thinking content"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50

        # Only text block, no thinking
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Simple response"
        mock_response.content = [mock_text_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_thinking=True)

            messages = [{"role": "user", "content": "Hello"}]
            result = await provider.generate(messages)

            assert result.content == "Simple response"
            # Should not have thinking metadata
            assert "thinking" not in result.metadata

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_thinking_no_cache(self):
        """Test Anthropic generate with thinking but no cache metrics"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"

        # Create usage object without cache attributes
        mock_usage = type("obj", (object,), {"input_tokens": 100, "output_tokens": 50})()
        mock_response.usage = mock_usage

        # Mock thinking block
        mock_thinking_block = MagicMock()
        mock_thinking_block.type = "thinking"
        mock_thinking_block.thinking = "Reasoning..."

        # Mock text block
        mock_text_block = MagicMock()
        mock_text_block.type = "text"
        mock_text_block.text = "Response with thinking"

        mock_response.content = [mock_thinking_block, mock_text_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", use_thinking=True)

            messages = [{"role": "user", "content": "Complex task"}]
            result = await provider.generate(messages)

            assert result.content == "Response with thinking"
            assert result.metadata["thinking"] == "Reasoning..."
            # Should not have cache metrics
            assert "cache_creation_tokens" not in result.metadata

    @pytest.mark.asyncio
    async def test_anthropic_analyze_large_codebase(self):
        """Test Anthropic analyze_large_codebase method"""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model = "claude-3-sonnet"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 1000
        mock_response.usage.output_tokens = 500

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Analysis complete"
        mock_response.content = [mock_block]

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key")

            codebase_files = [
                {"path": "main.py", "content": "print('hello')"},
                {"path": "utils.py", "content": "def helper(): pass"},
            ]
            result = await provider.analyze_large_codebase(codebase_files, "Analyze this code")

            assert result.content == "Analysis complete"
            assert result.tokens_used == 1500


class TestSamplingParamNormalization:
    """Opus 4.7+ and Claude 5 reject temperature/top_p/top_k + enabled-thinking (400)."""

    def test_normalize_strips_sampling_params_for_opus_48(self):
        from attune.llm.providers.anthropic import _normalize_api_kwargs_for_model

        kw = {"model": "claude-opus-4-8", "temperature": 0.7, "top_p": 0.9, "top_k": 5}
        _normalize_api_kwargs_for_model(kw)
        assert "temperature" not in kw and "top_p" not in kw and "top_k" not in kw

    def test_normalize_strips_sampling_params_for_claude_5_family(self):
        """Live 400 on claude-sonnet-5 (integration-auth, 2026-07-06)."""
        from attune.llm.providers.anthropic import _normalize_api_kwargs_for_model

        for model in ("claude-sonnet-5", "claude-fable-5", "claude-sonnet-5-20260301"):
            kw = {"model": model, "temperature": 0.7, "top_p": 0.9}
            _normalize_api_kwargs_for_model(kw)
            assert "temperature" not in kw and "top_p" not in kw, model

    def test_normalize_keeps_sampling_params_for_older_models(self):
        from attune.llm.providers.anthropic import _normalize_api_kwargs_for_model

        for model in ("claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-6"):
            kw = {"model": model, "temperature": 0.7}
            _normalize_api_kwargs_for_model(kw)
            assert kw["temperature"] == 0.7, model

    def test_normalize_converts_enabled_thinking_to_adaptive_for_opus_48(self):
        from attune.llm.providers.anthropic import _normalize_api_kwargs_for_model

        kw = {"model": "claude-opus-4-8", "thinking": {"type": "enabled", "budget_tokens": 10000}}
        _normalize_api_kwargs_for_model(kw)
        assert kw["thinking"] == {"type": "adaptive"}

    @pytest.mark.asyncio
    async def test_generate_omits_temperature_for_opus_48(self):
        """End-to-end: an Opus 4.8 call must not send temperature (would 400)."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.model = "claude-opus-4-8"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        block = MagicMock()
        block.type = "text"
        block.text = "ok"
        mock_response.content = [block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", model="claude-opus-4-8")
            await provider.generate([{"role": "user", "content": "hi"}], temperature=0.7)

        sent = mock_client.messages.create.await_args.kwargs
        assert "temperature" not in sent
        assert sent["model"] == "claude-opus-4-8"

    @pytest.mark.asyncio
    async def test_generate_keeps_temperature_for_sonnet_45(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.model = "claude-sonnet-4-5"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        block = MagicMock()
        block.type = "text"
        block.text = "ok"
        mock_response.content = [block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-4-5")
            await provider.generate([{"role": "user", "content": "hi"}], temperature=0.3)

        sent = mock_client.messages.create.await_args.kwargs
        # SDK 1.x contract (#2243): sampling params ride in extra_body
        assert sent["extra_body"]["temperature"] == 0.3
        assert "temperature" not in sent

    @pytest.mark.asyncio
    async def test_generate_omits_temperature_for_sonnet_5(self):
        """End-to-end: a Claude 5 call must not send temperature (would 400)."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.model = "claude-sonnet-5"
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=1, output_tokens=1)
        block = MagicMock()
        block.type = "text"
        block.text = "ok"
        mock_response.content = [block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            provider = AnthropicProvider(api_key="test-key", model="claude-sonnet-5")
            await provider.generate([{"role": "user", "content": "hi"}], temperature=0.3)

        sent = mock_client.messages.create.await_args.kwargs
        assert "temperature" not in sent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
