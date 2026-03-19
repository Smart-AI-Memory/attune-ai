"""Unit tests for RateLimiter sliding-window implementation.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

from attune.mcp.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the sliding-window rate limiter."""

    def test_allows_calls_within_limit(self):
        """Calls within max_calls are allowed."""
        limiter = RateLimiter(max_calls=5, window_seconds=60.0)
        for _ in range(5):
            assert limiter.check("tool_a") is True

    def test_blocks_calls_over_limit(self):
        """The (max_calls + 1)th call is blocked."""
        limiter = RateLimiter(max_calls=3, window_seconds=60.0)
        for _ in range(3):
            assert limiter.check("tool_a") is True
        assert limiter.check("tool_a") is False

    def test_window_expiry_allows_new_calls(self):
        """After the window expires, calls are allowed again."""
        limiter = RateLimiter(max_calls=2, window_seconds=10.0)
        base_time = 1000.0

        with patch("time.monotonic", return_value=base_time):
            assert limiter.check("tool_a") is True
            assert limiter.check("tool_a") is True
            assert limiter.check("tool_a") is False

        # Advance past the window
        with patch("time.monotonic", return_value=base_time + 11.0):
            assert limiter.check("tool_a") is True

    def test_independent_keys(self):
        """Rate limits are tracked independently per key."""
        limiter = RateLimiter(max_calls=2, window_seconds=60.0)
        assert limiter.check("tool_a") is True
        assert limiter.check("tool_a") is True
        assert limiter.check("tool_a") is False

        # Different key is not affected
        assert limiter.check("tool_b") is True
        assert limiter.check("tool_b") is True

    def test_default_limits(self):
        """Default limits are 60 calls per 60 seconds."""
        limiter = RateLimiter()
        assert limiter._max == 60
        assert limiter._window == 60.0

    def test_custom_limits(self):
        """Custom limits are stored correctly."""
        limiter = RateLimiter(max_calls=100, window_seconds=30.0)
        assert limiter._max == 100
        assert limiter._window == 30.0

    def test_pruning_removes_old_timestamps(self):
        """Old timestamps outside the window are pruned."""
        limiter = RateLimiter(max_calls=10, window_seconds=5.0)
        base_time = 1000.0

        # Add 3 calls at base_time
        with patch("time.monotonic", return_value=base_time):
            limiter.check("tool_a")
            limiter.check("tool_a")
            limiter.check("tool_a")

        assert len(limiter._calls["tool_a"]) == 3

        # Check at base_time + 6 — old entries should be pruned
        with patch("time.monotonic", return_value=base_time + 6.0):
            limiter.check("tool_a")

        assert len(limiter._calls["tool_a"]) == 1

    def test_blocked_call_does_not_add_timestamp(self):
        """A blocked call should not record a timestamp."""
        limiter = RateLimiter(max_calls=2, window_seconds=60.0)
        limiter.check("tool_a")
        limiter.check("tool_a")
        assert limiter.check("tool_a") is False
        # Only 2 timestamps should be recorded, not 3
        assert len(limiter._calls["tool_a"]) == 2

    def test_empty_key_works(self):
        """Empty string as key is handled correctly."""
        limiter = RateLimiter(max_calls=1, window_seconds=60.0)
        assert limiter.check("") is True
        assert limiter.check("") is False
