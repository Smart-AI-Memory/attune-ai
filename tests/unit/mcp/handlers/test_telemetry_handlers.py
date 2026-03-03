"""Unit tests for attune.mcp.handlers.telemetry_handlers module.

Tests cover:
- get_telemetry_stats returns success=True
- get_telemetry_stats uses default days=30 when not provided
- get_telemetry_stats uses custom days when provided
- get_telemetry_stats returns expected zero values for cost/savings/cache_hit_rate

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock

import pytest

from attune.mcp.handlers.telemetry_handlers import get_telemetry_stats


def _make_server() -> MagicMock:
    """Build a minimal MagicMock server for telemetry handler tests.

    Returns:
        MagicMock server instance.

    """
    return MagicMock()


@pytest.mark.unit
class TestGetTelemetryStats:
    """Tests for get_telemetry_stats handler function."""

    async def test_returns_success_true(self) -> None:
        """Test that get_telemetry_stats always returns success=True."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        assert result["success"] is True

    async def test_default_days_is_30(self) -> None:
        """Test that days defaults to 30 when not provided in args."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        assert result["days"] == 30

    async def test_custom_days_value_is_used(self) -> None:
        """Test that a provided days value overrides the default."""
        server = _make_server()
        result = await get_telemetry_stats(server, {"days": 7})
        assert result["days"] == 7

    async def test_total_cost_is_zero(self) -> None:
        """Test that total_cost is 0.0 (placeholder implementation)."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        assert result["total_cost"] == 0.0

    async def test_savings_is_zero(self) -> None:
        """Test that savings is 0.0 (placeholder implementation)."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        assert result["savings"] == 0.0

    async def test_cache_hit_rate_is_zero(self) -> None:
        """Test that cache_hit_rate is 0.0 (placeholder implementation)."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        assert result["cache_hit_rate"] == 0.0

    async def test_result_contains_all_expected_keys(self) -> None:
        """Test that result dict contains all expected keys."""
        server = _make_server()
        result = await get_telemetry_stats(server, {})
        expected_keys = {"success", "days", "total_cost", "savings", "cache_hit_rate"}
        assert expected_keys.issubset(result.keys())

    async def test_custom_days_90(self) -> None:
        """Test with 90 days to ensure arbitrary values are forwarded."""
        server = _make_server()
        result = await get_telemetry_stats(server, {"days": 90})
        assert result["days"] == 90

    async def test_server_argument_is_accepted(self) -> None:
        """Test that the server argument is accepted without error."""
        server = _make_server()
        result = await get_telemetry_stats(server, {"days": 14})
        assert isinstance(result, dict)

    async def test_extra_args_do_not_affect_result(self) -> None:
        """Test that extra unknown keys in args are ignored gracefully."""
        server = _make_server()
        result = await get_telemetry_stats(server, {"days": 30, "unknown_key": "x"})
        assert result["success"] is True
        assert result["days"] == 30
