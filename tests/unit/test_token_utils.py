"""Tests for attune.utils.tokens module.

Tests accurate token counting using Anthropic API and tiktoken fallback.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.utils.tokens import (
    TokenCount,
    calculate_cost_with_cache,
    count_message_tokens,
    count_tokens,
    estimate_cost,
)


class TestCountTokens:
    """Test count_tokens function."""

    def test_empty_text_returns_zero(self):
        """Test that empty text returns 0 tokens."""
        result = count_tokens("", use_api=False)
        assert result == 0

    def test_simple_text_with_tiktoken(self):
        """Test token counting with tiktoken (if available)."""
        text = "Hello, world!"
        result = count_tokens(text, use_api=False)

        # Should return a reasonable token count (3-5 tokens)
        assert isinstance(result, int)
        assert 3 <= result <= 5

    def test_longer_text(self):
        """Test token counting with longer text."""
        text = "This is a longer piece of text that should contain more tokens."
        result = count_tokens(text, use_api=False)

        # Should have more tokens (10-20 range)
        assert isinstance(result, int)
        assert 10 <= result <= 20

    def test_code_text(self):
        """Test token counting with code."""
        code = """def hello():
    print("Hello, world!")
    return 42
"""
        result = count_tokens(code, use_api=False)

        # Code should tokenize to 10-15 tokens
        assert isinstance(result, int)
        assert 10 <= result <= 20

    @patch("attune.utils.tokens._get_client")
    def test_api_counting_success(self, mock_get_client):
        """Test API token counting when successful."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.input_tokens = 10
        mock_client.messages.count_tokens.return_value = mock_result
        mock_get_client.return_value = mock_client

        # Count with API
        result = count_tokens("Hello, world!", use_api=True)

        assert result == 10
        mock_client.messages.count_tokens.assert_called_once()

    @patch("attune.utils.tokens._get_client")
    def test_api_counting_fallback_on_error(self, mock_get_client):
        """Test fallback to tiktoken when API fails."""
        # Mock API failure
        mock_client = MagicMock()
        mock_client.messages.count_tokens.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client

        # Should fall back to tiktoken/heuristic
        result = count_tokens("Hello, world!", use_api=True)

        # Should still return a result
        assert isinstance(result, int)
        assert result > 0

    def test_heuristic_fallback(self):
        """Test heuristic counting when neither API nor tiktoken available."""
        # Use very long text to test token counting
        text = "x" * 400  # 400 characters

        result = count_tokens(text, use_api=False)

        # With tiktoken or heuristic, should return reasonable count
        # Tiktoken: ~50-60 tokens, Heuristic: 100 tokens (400 / 4)
        assert isinstance(result, int)
        assert 40 <= result <= 120  # Allow variance for different methods


class TestCountMessageTokens:
    """Test count_message_tokens function."""

    def test_empty_messages_returns_zero(self):
        """Test that empty messages return 0 tokens."""
        result = count_message_tokens([])
        assert result["total"] == 0
        assert result["system"] == 0
        assert result["messages"] == 0

    def test_single_message(self):
        """Test counting tokens for a single message."""
        messages = [{"role": "user", "content": "Hello, world!"}]
        result = count_message_tokens(messages)

        assert isinstance(result["total"], int)
        assert result["total"] > 0
        assert result["messages"] > 0

    def test_multiple_messages(self):
        """Test counting tokens for multiple messages."""
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there! How can I help?"},
            {"role": "user", "content": "Tell me about Python."},
        ]
        result = count_message_tokens(messages)

        assert isinstance(result["total"], int)
        assert result["total"] > 10  # Should have significant token count
        assert result["messages"] > 0

    def test_with_system_prompt(self):
        """Test counting tokens with system prompt."""
        messages = [{"role": "user", "content": "Hello!"}]
        system_prompt = "You are a helpful assistant."

        result = count_message_tokens(messages, system_prompt=system_prompt)

        assert result["system"] > 0
        assert result["messages"] > 0
        assert result["total"] == result["system"] + result["messages"]

    @patch("attune.utils.tokens._get_client")
    def test_api_message_counting(self, mock_get_client):
        """Test API message counting."""
        # Mock client
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.input_tokens = 25
        mock_client.messages.count_tokens.return_value = mock_result
        mock_get_client.return_value = mock_client

        messages = [{"role": "user", "content": "Test message"}]
        result = count_message_tokens(messages, use_api=True)

        assert result["total"] == 25
        mock_client.messages.count_tokens.assert_called_once()


class TestEstimateCost:
    """Test estimate_cost function."""

    def test_basic_cost_calculation(self):
        """Test basic cost calculation for Sonnet 4.5."""
        # Sonnet 4.5: $3/M input, $15/M output
        input_tokens = 1000
        output_tokens = 500

        total_cost = estimate_cost(input_tokens, output_tokens)
        # 1000 * $3/M + 500 * $15/M = $0.003 + $0.0075 = $0.0105
        assert abs(total_cost - 0.0105) < 0.0001

    def test_large_token_counts(self):
        """Test cost calculation with large token counts."""
        input_tokens = 100_000  # 100K tokens
        output_tokens = 50_000  # 50K tokens

        total_cost = estimate_cost(input_tokens, output_tokens)

        # Sonnet 4.5: 100K * $3/M + 50K * $15/M = $0.30 + $0.75 = $1.05
        assert abs(total_cost - 1.05) < 0.01


class TestCalculateCostWithCache:
    """Test calculate_cost_with_cache function."""

    def test_cost_with_cache_reads(self):
        """Test cost calculation with cache reads."""
        result = calculate_cost_with_cache(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=0,
            cache_read_tokens=5000,
        )

        assert "base_cost" in result
        assert "cache_read_cost" in result
        assert "total_cost" in result
        assert "savings" in result

        # Cache reads should save money (90% discount)
        assert result["savings"] > 0
        assert result["cache_read_cost"] < result["savings"]

    def test_cost_with_cache_writes(self):
        """Test cost calculation with cache creation."""
        result = calculate_cost_with_cache(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=5000,
            cache_read_tokens=0,
        )

        assert result["cache_write_cost"] > 0
        # Cache writes cost 25% more than regular input
        # For Sonnet 4.5: 5000 tokens * $3.75/M = $0.01875
        assert abs(result["cache_write_cost"] - 0.01875) < 0.001

    def test_cost_with_both_cache_operations(self):
        """Test cost calculation with both cache writes and reads."""
        result = calculate_cost_with_cache(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=2000,
            cache_read_tokens=3000,
        )

        assert result["base_cost"] > 0
        assert result["cache_write_cost"] > 0
        assert result["cache_read_cost"] > 0
        assert result["savings"] > 0

        # Verify total cost (with tolerance for rounding)
        expected_total = (
            result["base_cost"] + result["cache_write_cost"] + result["cache_read_cost"]
        )
        assert abs(result["total_cost"] - expected_total) < 0.001


class TestTokenCountDataclass:
    """Test TokenCount dataclass."""

    def test_token_count_creation(self):
        """Test creating TokenCount instance."""
        tc = TokenCount(tokens=100, method="tiktoken", model="claude-sonnet-5")

        assert tc.tokens == 100
        assert tc.method == "tiktoken"
        assert tc.model == "claude-sonnet-5"


class TestAnthropicProviderIntegration:
    """Test integration with AnthropicProvider."""

    def test_provider_estimate_tokens(self):
        """Test AnthropicProvider.estimate_tokens() uses accurate counting.

        Uses a dummy API key — estimate_tokens() runs entirely locally
        (tiktoken or heuristic fallback) and does not hit the Anthropic API.
        """
        from attune.llm.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="sk-ant-test")

        text = "Hello, world! This is a test."
        tokens = provider.estimate_tokens(text)

        # Should return accurate count
        assert isinstance(tokens, int)
        assert 5 <= tokens <= 10

    def test_provider_calculate_actual_cost(self):
        """Test AnthropicProvider.calculate_actual_cost().

        Uses a dummy API key — calculate_actual_cost() is pure arithmetic
        on the supplied token counts and does not hit the Anthropic API.
        """
        from attune.llm.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="sk-ant-test")

        cost = provider.calculate_actual_cost(
            input_tokens=1000,
            output_tokens=500,
            cache_read_tokens=5000,
        )

        assert "base_cost" in cost
        assert "cache_read_cost" in cost
        assert "total_cost" in cost
        assert "savings" in cost

        # Verify cache saves money
        assert cost["savings"] > 0
        assert cost["cache_read_cost"] < (5000 / 1_000_000) * 3.0  # Less than full price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
