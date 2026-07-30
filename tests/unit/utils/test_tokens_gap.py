"""Coverage tests for remaining token utility success paths.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from types import SimpleNamespace

import pytest

from attune.utils.tokens import (
    calculate_cost_with_cache,
    count_message_tokens,
    count_tokens,
    estimate_cost,
)


class TestCountTokens:
    """Cover token-counting success paths."""

    def test_empty_text_returns_zero(self):
        """Return zero immediately for empty text."""
        assert count_tokens("") == 0

    def test_api_success_returns_exact_count_without_fallback(self, monkeypatch):
        """Return the API token count without invoking local fallbacks."""

        class Messages:
            def count_tokens(self, **kwargs):
                assert kwargs == {
                    "model": "claude-sonnet-5",
                    "messages": [{"role": "user", "content": "Hello"}],
                }
                return SimpleNamespace(input_tokens=42)

        client = SimpleNamespace(messages=Messages())

        def fail_fallback(*args, **kwargs):
            pytest.fail("fallback token counting should not run")

        monkeypatch.setattr("attune.utils.tokens._client", None)
        monkeypatch.setattr("attune.utils.tokens._get_client", lambda: client)
        monkeypatch.setattr(
            "attune.utils.tokens._count_tokens_tiktoken",
            fail_fallback,
        )
        monkeypatch.setattr(
            "attune.utils.tokens._count_tokens_heuristic",
            fail_fallback,
        )

        assert count_tokens("Hello", use_api=True) == 42


class TestCountMessageTokens:
    """Cover conversation-counting success paths."""

    def test_empty_messages_without_system_prompt_returns_zero_counts(self):
        """Return an all-zero breakdown for an empty conversation."""
        assert count_message_tokens([], system_prompt=None) == {
            "system": 0,
            "messages": 0,
            "total": 0,
        }

    def test_non_api_without_system_includes_role_overhead(self, monkeypatch):
        """Add four tokens of role overhead to every message."""
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        token_counts = {"first": 3, "second": 5}

        monkeypatch.setattr(
            "attune.utils.tokens.count_tokens",
            lambda text, model="claude-sonnet-5", use_api=False: token_counts[text],
        )

        counts = count_message_tokens(messages, system_prompt=None)

        assert counts["system"] == 0
        assert counts["messages"] == 3 + 4 + 5 + 4
        assert counts["total"] == counts["messages"]


class TestCostCalculation:
    """Cover cost calculation through the model registry."""

    def test_estimate_cost_uses_registry_pricing(self):
        """Calculate input and output costs using real registry pricing."""
        assert estimate_cost(1_000_000, 1_000_000) == 18.0

    def test_estimate_cost_rejects_unknown_model(self, monkeypatch):
        """Propagate ValueError when registry pricing is unavailable."""
        monkeypatch.setattr(
            "attune.models.registry.get_pricing_for_model",
            lambda model: None,
        )

        with pytest.raises(ValueError, match=r"^Unknown model: missing-model$"):
            estimate_cost(1, 1, model="missing-model")

    def test_calculate_cost_with_cache_uses_registry_pricing(self):
        """Calculate cache costs and savings using real registry pricing."""
        costs = calculate_cost_with_cache(
            input_tokens=1_000_000,
            output_tokens=0,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )

        assert costs["base_cost"] == round(3.0, 6)
        assert costs["cache_write_cost"] == round(3.75, 6)
        assert costs["cache_read_cost"] == round(0.3, 6)
        assert costs["total_cost"] == round(7.05, 6)
        assert costs["savings"] == round(2.7, 6)
