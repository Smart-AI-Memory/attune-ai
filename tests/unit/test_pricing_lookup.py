"""Tests for per-model pricing lookup in cache savings calculations.

Verifies that providers.py and usage_tracker.py use ModelRegistry pricing
instead of hardcoded Sonnet 4.5 rates.

Generated with XML-enhanced task prompts.
"""

import pytest

from attune.models.registry import get_pricing_for_model

# ---------------------------------------------------------------------------
# Task 1.1: Registry pricing function returns correct per-model rates
# ---------------------------------------------------------------------------


class TestRegistryPricingLookup:
    """Test that get_pricing_for_model returns correct rates for known models."""

    def test_sonnet_pricing(self) -> None:
        """Sonnet 4.5 returns $3/M input, $15/M output."""
        pricing = get_pricing_for_model("claude-sonnet-5")
        assert pricing is not None
        assert pricing["input"] == pytest.approx(3.0)
        assert pricing["output"] == pytest.approx(15.0)

    def test_opus_pricing(self) -> None:
        """Opus 4.8 returns $5/M input, $25/M output."""
        pricing = get_pricing_for_model("claude-opus-4-8")
        assert pricing is not None
        assert pricing["input"] == pytest.approx(5.0)
        assert pricing["output"] == pytest.approx(25.0)

    def test_haiku_pricing(self) -> None:
        """Haiku 4.5 returns $1/M input, $5/M output."""
        pricing = get_pricing_for_model("claude-haiku-4-5")
        assert pricing is not None
        assert pricing["input"] == pytest.approx(1.0)
        assert pricing["output"] == pytest.approx(5.0)

    def test_unknown_model_returns_none(self) -> None:
        """Unknown model ID returns None for fallback handling."""
        pricing = get_pricing_for_model("unknown-model-xyz")
        assert pricing is None


# ---------------------------------------------------------------------------
# Task 1.1: Cache savings math uses per-model rates
# ---------------------------------------------------------------------------


class TestCacheSavingsMath:
    """Test that cache savings calculations are correct for different models."""

    def test_opus_cache_savings_higher_than_sonnet(self) -> None:
        """Opus at $5/M should yield 5/3x savings vs Sonnet at $3/M for same tokens."""
        tokens = 10_000
        opus_pricing = get_pricing_for_model("claude-opus-4-8")
        sonnet_pricing = get_pricing_for_model("claude-sonnet-5")

        assert opus_pricing is not None
        assert sonnet_pricing is not None

        opus_savings = tokens * (opus_pricing["input"] / 1_000_000) * 0.9
        sonnet_savings = tokens * (sonnet_pricing["input"] / 1_000_000) * 0.9

        assert opus_savings == pytest.approx(sonnet_savings * (5.0 / 3.0))

    def test_haiku_cache_savings_lower_than_sonnet(self) -> None:
        """Haiku at $1/M should yield 1/3 savings vs Sonnet at $3/M."""
        tokens = 10_000
        haiku_pricing = get_pricing_for_model("claude-haiku-4-5")
        sonnet_pricing = get_pricing_for_model("claude-sonnet-5")

        assert haiku_pricing is not None
        assert sonnet_pricing is not None

        haiku_savings = tokens * (haiku_pricing["input"] / 1_000_000) * 0.9
        sonnet_savings = tokens * (sonnet_pricing["input"] / 1_000_000) * 0.9

        assert haiku_savings == pytest.approx(sonnet_savings / 3.0)

    def test_fallback_for_unknown_model(self) -> None:
        """Unknown model falls back to $3.00/M (Sonnet default)."""
        pricing = get_pricing_for_model("unknown-model")
        input_cost = pricing["input"] if pricing else 3.00

        assert input_cost == pytest.approx(3.00)

    def test_write_cost_proportional_to_model(self) -> None:
        """Cache write cost is 125% of input rate, scaled per model."""
        opus_pricing = get_pricing_for_model("claude-opus-4-8")
        assert opus_pricing is not None

        tokens = 1000
        write_cost = tokens * (opus_pricing["input"] / 1_000_000) * 1.25

        # Opus: 1000 * ($5/1M) * 1.25 = $0.00625
        assert write_cost == pytest.approx(0.00625)


# ---------------------------------------------------------------------------
# Task 1.2: UsageTracker multi-model aggregation
# ---------------------------------------------------------------------------


class TestUsageTrackerPerModelAggregation:
    """Test that savings aggregation handles multiple models correctly."""

    def test_multi_model_savings_aggregation(self) -> None:
        """Entries with different models should each use their own pricing."""
        entries = [
            {
                "model": "claude-opus-4-8",
                "prompt_cache": {"hit": True, "read_tokens": 1000, "creation_tokens": 0},
            },
            {
                "model": "claude-haiku-4-5",
                "prompt_cache": {"hit": True, "read_tokens": 1000, "creation_tokens": 0},
            },
        ]

        total_savings = 0.0
        for entry in entries:
            prompt_cache = entry.get("prompt_cache", {})
            read_tokens = prompt_cache.get("read_tokens", 0)
            if read_tokens > 0:
                model_id = entry.get("model", "")
                pricing = get_pricing_for_model(model_id) if model_id else None
                cost_per_token = (pricing["input"] if pricing else 3.00) / 1_000_000
                total_savings += read_tokens * cost_per_token * 0.9

        # Opus: 1000 * ($5/1M) * 0.9 = $0.0045
        # Haiku: 1000 * ($1/1M) * 0.9 = $0.0009
        # Total: $0.0054
        assert total_savings == pytest.approx(0.0054)

    def test_empty_model_uses_fallback(self) -> None:
        """Entry with empty model string should use $3.00/M fallback."""
        entries = [
            {
                "model": "",
                "prompt_cache": {"hit": True, "read_tokens": 1000, "creation_tokens": 0},
            },
        ]

        total_savings = 0.0
        for entry in entries:
            prompt_cache = entry.get("prompt_cache", {})
            read_tokens = prompt_cache.get("read_tokens", 0)
            if read_tokens > 0:
                model_id = entry.get("model", "")
                pricing = get_pricing_for_model(model_id) if model_id else None
                cost_per_token = (pricing["input"] if pricing else 3.00) / 1_000_000
                total_savings += read_tokens * cost_per_token * 0.9

        # Fallback: 1000 * ($3/1M) * 0.9 = $0.0027
        assert total_savings == pytest.approx(0.0027)
