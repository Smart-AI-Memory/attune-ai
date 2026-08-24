"""Unit tests for telemetry handler method on AttuneMCPServer.

Tests cover _get_telemetry_stats() which delegates to UsageTracker.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


def _make_server() -> AttuneMCPServer:
    """Build a minimal server instance."""
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return AttuneMCPServer()


_FAKE_STATS = {
    "total_calls": 42,
    "total_cost": 1.25,
    "total_tokens_input": 5000,
    "total_tokens_output": 2000,
    "cache_hits": 10,
    "cache_misses": 32,
    "cache_hit_rate": 23.8,
    "by_tier": {},
    "by_workflow": {},
    "by_provider": {},
}


@pytest.mark.unit
class TestGetTelemetryStats:
    """Tests for _get_telemetry_stats handler method."""

    async def test_returns_success_with_real_tracker(self) -> None:
        """Test that result includes success=True when tracker works."""
        server = _make_server()
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = _FAKE_STATS.copy()

        with patch(
            "attune.mcp.server.UsageTracker",
            return_value=mock_tracker,
            create=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "attune.telemetry.usage_tracker": MagicMock(
                        UsageTracker=MagicMock(return_value=mock_tracker)
                    )
                },
            ):
                result = await server._get_telemetry_stats({})

        assert result["success"] is True
        assert result["total_cost"] == 1.25
        assert result["total_calls"] == 42

    async def test_default_days_passed_to_tracker(self) -> None:
        """Test that days=30 is passed when not provided."""
        server = _make_server()
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = _FAKE_STATS.copy()

        with patch(
            "attune.telemetry.usage_tracker.UsageTracker",
            return_value=mock_tracker,
        ):
            result = await server._get_telemetry_stats({})

        mock_tracker.get_stats.assert_called_once_with(days=30)
        assert result["success"] is True

    async def test_custom_days_passed_to_tracker(self) -> None:
        """Test that custom days value is forwarded."""
        server = _make_server()
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = _FAKE_STATS.copy()

        with patch(
            "attune.telemetry.usage_tracker.UsageTracker",
            return_value=mock_tracker,
        ):
            result = await server._get_telemetry_stats({"days": 7})

        mock_tracker.get_stats.assert_called_once_with(days=7)
        assert result["success"] is True

    async def test_import_error_returns_failure(self) -> None:
        """Test graceful handling when telemetry module unavailable."""
        server = _make_server()

        with patch.dict(
            "sys.modules",
            {"attune.telemetry.usage_tracker": None},
        ):
            # Force fresh import attempt by clearing any cached import
            result = await server._get_telemetry_stats({})

        assert result["success"] is False
        assert "error" in result

    async def test_extra_args_ignored(self) -> None:
        """Test that extra args don't break the handler."""
        server = _make_server()
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = _FAKE_STATS.copy()

        with patch(
            "attune.telemetry.usage_tracker.UsageTracker",
            return_value=mock_tracker,
        ):
            result = await server._get_telemetry_stats({"days": 30, "unknown": "x"})

        assert result["success"] is True
