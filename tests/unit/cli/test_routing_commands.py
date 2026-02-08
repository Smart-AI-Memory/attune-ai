"""Tests for adaptive routing CLI commands.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from unittest.mock import MagicMock, patch

import pytest


class TestRoutingCommands:
    """Test suite for routing CLI commands."""

    @pytest.fixture
    def mock_telemetry(self):
        """Create mock telemetry tracker."""
        tracker = MagicMock()
        tracker.get_recent_entries.return_value = [
            {
                "workflow": "code-review",
                "stage": "analysis",
                "model": "claude-haiku-4-5-20251001",
                "tier": "CHEAP",
                "provider": "anthropic",
                "cost": 0.0016,
                "success": True,
                "duration_ms": 1200,
            },
            {
                "workflow": "code-review",
                "stage": "analysis",
                "model": "claude-sonnet-4-5-20250929",
                "tier": "CAPABLE",
                "provider": "anthropic",
                "cost": 0.0077,
                "success": True,
                "duration_ms": 2300,
            },
        ]

        tracker.get_stats.return_value = {
            "total_calls": 100,
            "total_cost": 1.50,
            "by_workflow": {
                "code-review": 0.80,
                "bug-predict": 0.70,
            },
            "cache_hit_rate": 45.0,
        }

        return tracker

    @pytest.fixture
    def mock_router(self):
        """Create mock adaptive router."""
        router = MagicMock()

        # Mock get_routing_stats
        router.get_routing_stats.return_value = {
            "workflow": "code-review",
            "stage": "all",
            "days_analyzed": 7,
            "models_used": ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20250929"],
            "performance_by_model": {
                "claude-haiku-4-5-20251001": {
                    "calls": 80,
                    "success_rate": 0.95,
                    "avg_cost": 0.0016,
                    "avg_latency_ms": 1200,
                },
                "claude-sonnet-4-5-20250929": {
                    "calls": 20,
                    "success_rate": 1.0,
                    "avg_cost": 0.0077,
                    "avg_latency_ms": 2300,
                },
            },
            "total_calls": 100,
            "avg_cost": 0.0029,
            "avg_success_rate": 0.96,
        }

        # Mock recommend_tier_upgrade
        router.recommend_tier_upgrade.return_value = (
            False,
            "Performance acceptable: 5.0% failure rate",
        )

        return router

    def test_routing_stats_command(self, mock_telemetry, mock_router, capsys):
        """Test routing stats command output."""
        from src.attune.cli.commands.routing import cmd_routing_stats

        # Mock dependencies
        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            with patch("src.attune.cli.commands.routing.AdaptiveModelRouter") as mock_router_class:
                mock_router_class.return_value = mock_router

                # Create mock args
                args = MagicMock()
                args.workflow = "code-review"
                args.stage = None
                args.days = 7

                # Execute command
                result = cmd_routing_stats(args)

                # Verify success
                assert result == 0

                # Verify router was called
                mock_router.get_routing_stats.assert_called_once_with(
                    workflow="code-review", stage=None, days=7
                )

                # Check output contains key info
                captured = capsys.readouterr()
                assert "ADAPTIVE ROUTING STATISTICS" in captured.out
                assert "code-review" in captured.out
                assert "100" in captured.out  # Total calls
                assert "claude-haiku-4-5-20251001" in captured.out

    def test_routing_stats_no_data(self, mock_telemetry, mock_router, capsys):
        """Test routing stats with no data."""
        from src.attune.cli.commands.routing import cmd_routing_stats

        # Mock router to return no data
        mock_router.get_routing_stats.return_value = {
            "workflow": "nonexistent",
            "stage": "all",
            "days_analyzed": 7,
            "models_used": [],
            "performance_by_model": {},
            "total_calls": 0,
            "avg_cost": 0.0,
            "avg_success_rate": 0.0,
        }

        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            with patch("src.attune.cli.commands.routing.AdaptiveModelRouter") as mock_router_class:
                mock_router_class.return_value = mock_router

                args = MagicMock()
                args.workflow = "nonexistent"
                args.stage = None
                args.days = 7

                result = cmd_routing_stats(args)

                # Should return error
                assert result == 1

                captured = capsys.readouterr()
                assert "No data found" in captured.out

    def test_routing_check_no_upgrade_needed(self, mock_telemetry, mock_router, capsys):
        """Test routing check when no upgrade is needed."""
        from src.attune.cli.commands.routing import cmd_routing_check

        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            with patch("src.attune.cli.commands.routing.AdaptiveModelRouter") as mock_router_class:
                mock_router_class.return_value = mock_router

                args = MagicMock()
                args.workflow = "code-review"
                args.stage = None
                args.all = False
                args.days = 7

                result = cmd_routing_check(args)

                assert result == 0

                captured = capsys.readouterr()
                assert "NO UPGRADE NEEDED" in captured.out
                assert "Performance acceptable" in captured.out

    def test_routing_check_upgrade_needed(self, mock_telemetry, mock_router, capsys):
        """Test routing check when upgrade is recommended."""
        from src.attune.cli.commands.routing import cmd_routing_check

        # Mock router to recommend upgrade
        mock_router.recommend_tier_upgrade.return_value = (
            True,
            "High failure rate: 25.0% (5/20 failed in recent calls)",
        )

        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            with patch("src.attune.cli.commands.routing.AdaptiveModelRouter") as mock_router_class:
                mock_router_class.return_value = mock_router

                args = MagicMock()
                args.workflow = "code-review"
                args.stage = None
                args.all = False
                args.days = 7

                result = cmd_routing_check(args)

                assert result == 0

                captured = capsys.readouterr()
                assert "TIER UPGRADE RECOMMENDED" in captured.out
                assert "High failure rate" in captured.out

    def test_routing_check_all_workflows(self, mock_telemetry, mock_router, capsys):
        """Test routing check for all workflows."""
        from src.attune.cli.commands.routing import cmd_routing_check

        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            with patch("src.attune.cli.commands.routing.AdaptiveModelRouter") as mock_router_class:
                mock_router_class.return_value = mock_router

                args = MagicMock()
                args.all = True
                args.days = 7

                result = cmd_routing_check(args)

                assert result == 0

                # Should check both workflows from telemetry
                assert mock_router.recommend_tier_upgrade.call_count == 2

                captured = capsys.readouterr()
                assert "Checking" in captured.out
                assert "workflow(s)" in captured.out

    def test_routing_models_command(self, mock_telemetry, capsys):
        """Test routing models command."""
        from src.attune.cli.commands.routing import cmd_routing_models

        with patch("src.attune.cli.commands.routing.UsageTracker") as mock_tracker_class:
            mock_tracker_class.get_instance.return_value = mock_telemetry

            args = MagicMock()
            args.provider = "anthropic"
            args.days = 7

            result = cmd_routing_models(args)

            assert result == 0

            captured = capsys.readouterr()
            assert "MODEL PERFORMANCE COMPARISON" in captured.out
            assert "ANTHROPIC" in captured.out
            assert "claude-haiku-4-5-20251001" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
