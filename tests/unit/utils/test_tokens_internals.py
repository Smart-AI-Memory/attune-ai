"""Coverage tests for attune.utils.tokens internal and fallback paths.

Complements tests/unit/test_token_utils.py by exercising the client
factory, tiktoken/heuristic fallbacks, error branches, and the
registry-import fallbacks in the cost helpers.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
from unittest.mock import MagicMock

import pytest

import attune.utils.tokens as tokens_mod
from attune.utils.tokens import (
    _count_tokens_heuristic,
    _count_tokens_tiktoken,
    _get_client,
    _get_tiktoken_encoding,
    calculate_cost_with_cache,
    count_message_tokens,
    count_tokens,
    estimate_cost,
)


@pytest.fixture(autouse=True)
def _reset_client():
    """Ensure the module-level Anthropic client cache starts clean."""
    tokens_mod._client = None
    yield
    tokens_mod._client = None


class TestGetClient:
    """Cover _get_client() success, caching, and error branches."""

    def test_creates_and_caches_client(self, monkeypatch):
        """A client is built once and reused on subsequent calls."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        fake_anthropic = MagicMock()
        sentinel = object()
        fake_anthropic.Anthropic.return_value = sentinel
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        first = _get_client()
        second = _get_client()

        assert first is sentinel
        assert second is sentinel
        # Constructed exactly once despite two calls (cached).
        fake_anthropic.Anthropic.assert_called_once_with(api_key="sk-ant-test")

    def test_missing_api_key_raises_value_error(self, monkeypatch):
        """No ANTHROPIC_API_KEY -> ValueError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        fake_anthropic = MagicMock()
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            _get_client()

    def test_missing_anthropic_package_raises_import_error(self, monkeypatch):
        """anthropic not importable -> ImportError with install hint."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # Setting the module to None makes `from anthropic import ...` raise.
        monkeypatch.setitem(sys.modules, "anthropic", None)

        with pytest.raises(ImportError, match="anthropic package required"):
            _get_client()


class TestTiktokenEncoding:
    """Cover _get_tiktoken_encoding() availability and failure branches."""

    def test_returns_none_when_unavailable(self, monkeypatch):
        """TIKTOKEN_AVAILABLE False -> None (no encoding)."""
        monkeypatch.setattr(tokens_mod, "TIKTOKEN_AVAILABLE", False)
        _get_tiktoken_encoding.cache_clear()

        assert _get_tiktoken_encoding("claude-sonnet-5") is None

        _get_tiktoken_encoding.cache_clear()

    def test_returns_none_on_encoding_error(self, monkeypatch):
        """tiktoken.get_encoding raising -> warning + None."""
        monkeypatch.setattr(tokens_mod, "TIKTOKEN_AVAILABLE", True)
        fake_tiktoken = MagicMock()
        fake_tiktoken.get_encoding.side_effect = RuntimeError("boom")
        monkeypatch.setattr(tokens_mod, "tiktoken", fake_tiktoken, raising=False)
        _get_tiktoken_encoding.cache_clear()

        assert _get_tiktoken_encoding("some-model") is None

        _get_tiktoken_encoding.cache_clear()


class TestCountTokensTiktoken:
    """Cover _count_tokens_tiktoken() branches."""

    def test_empty_text_returns_zero(self):
        assert _count_tokens_tiktoken("", "claude-sonnet-5") == 0

    def test_returns_zero_when_no_encoding(self, monkeypatch):
        """No encoding available -> 0."""
        monkeypatch.setattr(tokens_mod, "_get_tiktoken_encoding", lambda model: None)
        assert _count_tokens_tiktoken("hello", "claude-sonnet-5") == 0

    def test_returns_zero_on_encode_error(self, monkeypatch):
        """encoding.encode raising -> warning + 0."""
        bad_encoding = MagicMock()
        bad_encoding.encode.side_effect = RuntimeError("encode failed")
        monkeypatch.setattr(tokens_mod, "_get_tiktoken_encoding", lambda model: bad_encoding)
        assert _count_tokens_tiktoken("hello", "claude-sonnet-5") == 0


class TestCountTokensHeuristic:
    """Cover _count_tokens_heuristic() branches."""

    def test_empty_text_returns_zero(self):
        assert _count_tokens_heuristic("") == 0

    def test_nonempty_text_uses_four_chars_per_token(self):
        # 400 chars // 4 == 100
        assert _count_tokens_heuristic("x" * 400) == 100

    def test_short_text_returns_at_least_one(self):
        assert _count_tokens_heuristic("a") == 1


class TestCountTokensHeuristicFallthrough:
    """count_tokens falls through to heuristic when tiktoken yields 0."""

    def test_falls_back_to_heuristic(self, monkeypatch):
        monkeypatch.setattr(tokens_mod, "TIKTOKEN_AVAILABLE", True)
        monkeypatch.setattr(tokens_mod, "_count_tokens_tiktoken", lambda text, model: 0)
        # 40 chars // 4 == 10 via heuristic.
        assert count_tokens("y" * 40, use_api=False) == 10


class TestCountMessageTokensBranches:
    """Cover count_message_tokens() system-only and API branches."""

    def test_empty_messages_with_system_prompt(self):
        result = count_message_tokens([], system_prompt="You are helpful")
        assert result["messages"] == 0
        assert result["system"] > 0
        assert result["total"] == result["system"]

    def test_api_path_with_system_prompt(self, monkeypatch):
        """use_api with a system prompt estimates the system/message split."""
        fake_client = MagicMock()
        fake_result = MagicMock()
        fake_result.input_tokens = 100
        fake_client.messages.count_tokens.return_value = fake_result
        monkeypatch.setattr(tokens_mod, "_get_client", lambda: fake_client)

        result = count_message_tokens(
            [{"role": "user", "content": "Hello there"}],
            system_prompt="System prompt text",
            use_api=True,
        )

        assert result["total"] == 100
        assert result["system"] > 0
        assert result["messages"] == 100 - result["system"]
        # system kwarg was forwarded to the API.
        _, kwargs = fake_client.messages.count_tokens.call_args
        assert kwargs["system"] == "System prompt text"

    def test_api_path_without_system_prompt(self, monkeypatch):
        fake_client = MagicMock()
        fake_result = MagicMock()
        fake_result.input_tokens = 42
        fake_client.messages.count_tokens.return_value = fake_result
        monkeypatch.setattr(tokens_mod, "_get_client", lambda: fake_client)

        result = count_message_tokens([{"role": "user", "content": "Hi"}], use_api=True)

        assert result["system"] == 0
        assert result["messages"] == 42
        assert result["total"] == 42

    def test_api_failure_falls_back_to_local(self, monkeypatch):
        """API error during message counting -> local component counting."""
        fake_client = MagicMock()
        fake_client.messages.count_tokens.side_effect = RuntimeError("api down")
        monkeypatch.setattr(tokens_mod, "_get_client", lambda: fake_client)

        result = count_message_tokens(
            [{"role": "user", "content": "Hello"}],
            system_prompt="sys",
            use_api=True,
        )

        assert result["total"] == result["system"] + result["messages"]
        assert result["messages"] > 0


class TestEstimateCostBranches:
    """Cover estimate_cost() unknown-model and ImportError fallbacks."""

    def test_unknown_model_raises_then_default_pricing_used(self, monkeypatch):
        """get_pricing_for_model returning None -> ValueError is raised."""
        import attune.models.registry as registry

        monkeypatch.setattr(registry, "get_pricing_for_model", lambda m: None)
        with pytest.raises(ValueError, match="Unknown model"):
            estimate_cost(1000, 500, model="nonexistent-model")

    def test_import_error_uses_default_pricing(self, monkeypatch):
        """registry unimportable -> default Sonnet pricing fallback."""
        monkeypatch.setitem(sys.modules, "attune.models.registry", None)
        cost = estimate_cost(1_000_000, 1_000_000)
        # Default pricing: $3/M input + $15/M output = $18 for 1M each.
        assert cost == pytest.approx(18.0)


class TestCalculateCostWithCacheBranches:
    """Cover calculate_cost_with_cache() fallback branches."""

    def test_unknown_model_falls_back_to_default(self, monkeypatch):
        """get_pricing_for_model None -> ValueError caught -> default pricing."""
        import attune.models.registry as registry

        monkeypatch.setattr(registry, "get_pricing_for_model", lambda m: None)
        result = calculate_cost_with_cache(
            input_tokens=1_000_000,
            output_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            model="nonexistent-model",
        )
        # Default input pricing $3/M -> $3 for 1M input tokens.
        assert result["base_cost"] == pytest.approx(3.0)

    def test_import_error_falls_back_to_default(self, monkeypatch):
        """registry unimportable -> default pricing path."""
        monkeypatch.setitem(sys.modules, "attune.models.registry", None)
        result = calculate_cost_with_cache(
            input_tokens=0,
            output_tokens=1_000_000,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        # Default output pricing $15/M -> $15 for 1M output tokens.
        assert result["base_cost"] == pytest.approx(15.0)
