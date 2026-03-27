"""Unit tests for attune.workflows.document_gen.cost_management module.

Tests cover:
- DocGenCostMixin._estimate_cost: cost calculation from tokens
- DocGenCostMixin._track_cost: accumulation, warning, and limit logic
- DocGenCostMixin._auto_scale_tokens: section-based token scaling

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest

from attune.workflows.compat import ModelTier
from attune.workflows.document_gen.cost_management import DocGenCostMixin


class _FakeHost(DocGenCostMixin):
    """Minimal host for cost management mixin testing."""

    pass


@pytest.fixture
def host() -> _FakeHost:
    """Create a fresh cost mixin host."""
    return _FakeHost()


# ---------------------------------------------------------------------------
# _estimate_cost
# ---------------------------------------------------------------------------


class TestEstimateCost:
    """Tests for DocGenCostMixin._estimate_cost."""

    def test_cheap_tier_cost(self, host: _FakeHost) -> None:
        """Test cost calculation for CHEAP tier."""
        cost = host._estimate_cost(ModelTier.CHEAP, 1000, 1000)
        # CHEAP: input=0.00025/1K, output=0.00125/1K
        expected = (1000 / 1000) * 0.00025 + (1000 / 1000) * 0.00125
        assert abs(cost - expected) < 1e-8

    def test_capable_tier_cost(self, host: _FakeHost) -> None:
        """Test cost calculation for CAPABLE tier."""
        cost = host._estimate_cost(ModelTier.CAPABLE, 2000, 500)
        expected = (2000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert abs(cost - expected) < 1e-8

    def test_premium_tier_cost(self, host: _FakeHost) -> None:
        """Test cost calculation for PREMIUM tier."""
        cost = host._estimate_cost(ModelTier.PREMIUM, 1000, 1000)
        expected = (1000 / 1000) * 0.015 + (1000 / 1000) * 0.075
        assert abs(cost - expected) < 1e-8

    def test_zero_tokens_zero_cost(self, host: _FakeHost) -> None:
        """Test that zero tokens produce zero cost."""
        cost = host._estimate_cost(ModelTier.CHEAP, 0, 0)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# _track_cost
# ---------------------------------------------------------------------------


class TestTrackCost:
    """Tests for DocGenCostMixin._track_cost."""

    def test_accumulates_cost(self, host: _FakeHost) -> None:
        """Test that costs accumulate over multiple calls."""
        host._track_cost(ModelTier.CHEAP, 1000, 1000)
        first_cost = host._accumulated_cost

        host._track_cost(ModelTier.CHEAP, 1000, 1000)
        assert host._accumulated_cost > first_cost

    def test_warning_issued_at_threshold(self, host: _FakeHost) -> None:
        """Test that warning is issued when cost reaches threshold."""
        host.max_cost = 0.01
        host.cost_warning_threshold = 0.5  # 50%

        # Track enough cost to cross 50% of 0.01
        host._track_cost(ModelTier.PREMIUM, 1000, 1000)

        assert host._cost_warning_issued is True

    def test_warning_not_issued_below_threshold(self, host: _FakeHost) -> None:
        """Test no warning below threshold."""
        host.max_cost = 100.0
        host.cost_warning_threshold = 0.8

        host._track_cost(ModelTier.CHEAP, 10, 10)

        assert host._cost_warning_issued is False

    def test_should_stop_at_limit(self, host: _FakeHost) -> None:
        """Test should_stop is True when cost exceeds limit."""
        host.max_cost = 0.001

        _, should_stop = host._track_cost(ModelTier.PREMIUM, 1000, 1000)

        assert should_stop is True

    def test_should_not_stop_below_limit(self, host: _FakeHost) -> None:
        """Test should_stop is False when cost is below limit."""
        host.max_cost = 100.0

        _, should_stop = host._track_cost(ModelTier.CHEAP, 10, 10)

        assert should_stop is False

    def test_zero_max_cost_never_stops(self, host: _FakeHost) -> None:
        """Test that max_cost=0 disables cost limit checking."""
        host.max_cost = 0.0

        _, should_stop = host._track_cost(ModelTier.PREMIUM, 100000, 100000)

        assert should_stop is False

    def test_returns_cost_for_call(self, host: _FakeHost) -> None:
        """Test that the cost for the current call is returned."""
        cost, _ = host._track_cost(ModelTier.CHEAP, 1000, 1000)
        assert cost > 0


# ---------------------------------------------------------------------------
# _auto_scale_tokens
# ---------------------------------------------------------------------------


class TestAutoScaleTokens:
    """Tests for DocGenCostMixin._auto_scale_tokens."""

    def test_minimum_16000(self, host: _FakeHost) -> None:
        """Test minimum token count is 16000."""
        result = host._auto_scale_tokens(1)
        assert result == 16000

    def test_maximum_64000(self, host: _FakeHost) -> None:
        """Test maximum token count is 64000."""
        result = host._auto_scale_tokens(100)
        assert result == 64000

    def test_scaling_mid_range(self, host: _FakeHost) -> None:
        """Test scaling for mid-range section count."""
        result = host._auto_scale_tokens(15)
        assert result == 30000  # 15 * 2000

    def test_user_override(self, host: _FakeHost) -> None:
        """Test that user override takes precedence."""
        host._user_max_write_tokens = 50000
        result = host._auto_scale_tokens(1)
        assert result == 50000

    def test_user_override_none_uses_auto(self, host: _FakeHost) -> None:
        """Test that None user override falls through to auto."""
        host._user_max_write_tokens = None
        result = host._auto_scale_tokens(20)
        assert result == 40000  # 20 * 2000
