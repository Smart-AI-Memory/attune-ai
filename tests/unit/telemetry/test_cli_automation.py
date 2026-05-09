"""Tests for attune.telemetry.cli_automation plain-text fallback branches.

Covers previously-uncovered lines:
- Lines 21-23: ImportError for rich (RICH_AVAILABLE = False, Console = None)
- Lines 185-195: cmd_tier1_status plain-text fallback
- Lines 261-273: cmd_test_status plain-text fallback
- Lines 341-352: cmd_agent_performance plain-text fallback
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _args(hours=24):
    return SimpleNamespace(hours=hours)


def _make_analytics(
    routing_stats=None,
    test_stats=None,
    coverage_stats=None,
    agent_stats=None,
):
    analytics = MagicMock()
    analytics.routing_accuracy.return_value = routing_stats or {
        "total_tasks": 10,
        "successful_routing": 9,
        "accuracy_rate": 0.9,
        "avg_confidence": 0.85,
        "by_task_type": {"code-review": {"total": 5, "success": 5, "rate": 1.0}},
    }
    analytics.test_execution_trends.return_value = test_stats or {
        "total_executions": 20,
        "success_rate": 0.95,
        "avg_duration_seconds": 3.5,
        "total_tests_run": 500,
        "total_failures": 25,
        "most_failing_tests": [{"name": "test_foo", "failures": 3}],
    }
    analytics.coverage_progress.return_value = coverage_stats or {
        "current_coverage": 87.5,
    }
    analytics.agent_performance.return_value = agent_stats or {
        "by_agent": {
            "code-reviewer": {
                "assignments": 10,
                "completed": 9,
                "success_rate": 0.9,
                "avg_duration_hours": 2.5,
            }
        },
        "automation_rate": 0.85,
        "human_review_rate": 0.15,
    }
    return analytics


# ---------------------------------------------------------------------------
# RICH_AVAILABLE = False (import error fallback)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRichImportFallback:
    def test_module_imports_without_rich(self):
        """Module loads even when rich is not installed."""
        import sys

        # Remove rich from sys.modules to simulate absence
        saved = {}
        for key in list(sys.modules):
            if key.startswith("rich"):
                saved[key] = sys.modules.pop(key)

        # Force re-import of the module with rich unavailable
        module_key = "attune.telemetry.cli_automation"
        if module_key in sys.modules:
            del sys.modules[module_key]

        try:
            with patch.dict(
                "sys.modules",
                {
                    "rich": None,
                    "rich.console": None,
                    "rich.panel": None,
                    "rich.table": None,
                    "rich.text": None,
                },
            ):
                import attune.telemetry.cli_automation as mod

                # Module should load; RICH_AVAILABLE might be False or True
                # depending on whether rich is actually installed
                assert hasattr(mod, "RICH_AVAILABLE")
        finally:
            # Restore saved modules
            sys.modules.update(saved)
            # Remove the freshly imported module to avoid contaminating other tests
            sys.modules.pop("attune.telemetry.cli_automation", None)


# ---------------------------------------------------------------------------
# cmd_tier1_status — plain text fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdTier1StatusPlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_tier1_status prints plain text when RICH_AVAILABLE is False."""
        from attune.telemetry import cli_automation

        analytics = _make_analytics()
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch(
                "attune.models.telemetry.get_telemetry_store",
                return_value=mock_store,
            ),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=analytics,
            ),
        ):
            result = cli_automation.cmd_tier1_status(_args(hours=24))

        assert result == 0
        captured = capsys.readouterr()
        assert "Task Routing Report" in captured.out
        assert "Total Tasks" in captured.out

    def test_plain_text_with_no_task_types(self, capsys):
        """Plain text branch skips 'By Task Type' when dict is empty."""
        from attune.telemetry import cli_automation

        analytics = _make_analytics(
            routing_stats={
                "total_tasks": 0,
                "successful_routing": 0,
                "accuracy_rate": 0.0,
                "avg_confidence": 0.0,
                "by_task_type": {},
            }
        )
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_tier1_status(_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "By Task Type" not in captured.out

    def test_exception_returns_early(self, capsys):
        """Exception during analytics retrieval is caught and printed."""
        from attune.telemetry import cli_automation

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            side_effect=RuntimeError("store unavailable"),
        ):
            cli_automation.cmd_tier1_status(_args())

        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# cmd_test_status — plain text fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdTestStatusPlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_test_status prints plain text when RICH_AVAILABLE is False."""
        from attune.telemetry import cli_automation

        analytics = _make_analytics()
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_test_status(_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "Test Execution Status" in captured.out
        assert "Total Runs" in captured.out
        assert "Most Frequently Failing" in captured.out

    def test_plain_text_with_no_failing_tests(self, capsys):
        """Plain text branch skips failing tests section when list is empty."""
        from attune.telemetry import cli_automation

        analytics = _make_analytics(
            test_stats={
                "total_executions": 5,
                "success_rate": 1.0,
                "avg_duration_seconds": 2.0,
                "total_tests_run": 100,
                "total_failures": 0,
                "most_failing_tests": [],
            }
        )
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            cli_automation.cmd_test_status(_args())

        captured = capsys.readouterr()
        assert "Most Frequently" not in captured.out


# ---------------------------------------------------------------------------
# cmd_agent_performance — plain text fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdAgentPerformancePlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_agent_performance prints plain text when RICH_AVAILABLE is False."""
        from attune.telemetry import cli_automation

        analytics = _make_analytics()
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_agent_performance(_args(hours=168))

        assert result == 0
        captured = capsys.readouterr()
        assert "Agent Performance" in captured.out
        assert "Automation Rate" in captured.out
        assert "code-reviewer" in captured.out

    def test_exception_returns_early(self, capsys):
        """Exception during analytics retrieval is caught and printed."""
        from attune.telemetry import cli_automation

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            side_effect=ImportError("telemetry not available"),
        ):
            cli_automation.cmd_agent_performance(_args())

        captured = capsys.readouterr()
        assert "Error" in captured.out
