"""Tests for attune.telemetry.cli_automation plain-text fallback branches.

Covers previously-uncovered lines:
- Lines 21-23: ImportError for rich (RICH_AVAILABLE = False, Console = None)
- Lines 185-195: cmd_task_routing_report plain-text fallback
- Lines 261-273: cmd_test_status plain-text fallback
- Lines 341-352: cmd_agent_performance plain-text fallback
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _args(hours=24):
    return SimpleNamespace(hours=hours)


def _tier1_summary():
    """Return a fully-typed tier1_summary dict (avoids MagicMock format issues)."""
    return {
        "task_routing": {
            "total_tasks": 10,
            "accuracy_rate": 0.9,
            "avg_confidence": 0.85,
        },
        "test_execution": {
            "total_executions": 20,
            "success_rate": 0.95,
            "avg_duration_seconds": 3.5,
            "total_failures": 25,
        },
        "coverage": {
            "current_coverage": 87.5,
            "trend": "improving",
        },
        "agent_performance": {
            "by_agent": {"code-reviewer": {}},
            "automation_rate": 0.85,
            "human_review_rate": 0.15,
        },
    }


def _routing_stats(with_task_types=True):
    return {
        "total_tasks": 10,
        "successful_routing": 9,
        "accuracy_rate": 0.9,
        "avg_confidence": 0.85,
        "by_task_type": (
            {"code-review": {"total": 5, "success": 5, "rate": 1.0}} if with_task_types else {}
        ),
    }


def _test_stats(with_failures=True):
    return {
        "total_executions": 20,
        "success_rate": 0.95,
        "avg_duration_seconds": 3.5,
        "total_tests_run": 500,
        "total_failures": 25,
        "most_failing_tests": ([{"name": "test_foo", "failures": 3}] if with_failures else []),
    }


def _coverage_stats():
    return {"current_coverage": 87.5}


def _agent_stats():
    return {
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


# ---------------------------------------------------------------------------
# RICH_AVAILABLE = False (import error fallback)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRichImportFallback:
    def test_module_imports_without_rich(self):
        """Module loads even when rich is not installed (covers lines 21-23)."""
        import sys

        # Stash rich modules
        saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("rich")}
        module_key = "attune.telemetry.cli_automation"
        sys.modules.pop(module_key, None)

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
                import attune.telemetry.cli_automation as mod  # noqa: F401

                assert hasattr(mod, "RICH_AVAILABLE")
        finally:
            sys.modules.update(saved)
            sys.modules.pop("attune.telemetry.cli_automation", None)


# ---------------------------------------------------------------------------
# cmd_tier1_status — plain text fallback (lines 92-118)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdTier1StatusPlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_tier1_status plain-text path prints all sections."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.tier1_summary.return_value = _tier1_summary()
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_tier1_status(_args(hours=24))

        assert result == 0
        captured = capsys.readouterr()
        assert "Tier 1 Automation Status" in captured.out
        assert "Task Routing" in captured.out
        assert "Test Execution" in captured.out

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
# cmd_task_routing_report — plain text fallback (lines 185-195)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdTaskRoutingReportPlainText:
    def test_plain_text_with_task_types(self, capsys):
        """Plain text fallback includes by-task-type breakdown."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.task_routing_accuracy.return_value = _routing_stats(with_task_types=True)
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_task_routing_report(_args(hours=24))

        assert result == 0
        captured = capsys.readouterr()
        assert "Task Routing Report" in captured.out
        assert "Total Tasks" in captured.out
        assert "By Task Type" in captured.out

    def test_plain_text_without_task_types(self, capsys):
        """Plain text branch skips 'By Task Type' when dict is empty."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.task_routing_accuracy.return_value = _routing_stats(with_task_types=False)
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_task_routing_report(_args())

        assert result == 0
        captured = capsys.readouterr()
        assert "By Task Type" not in captured.out

    def test_no_tasks_returns_early(self, capsys):
        """Returns 0 with message when no task data exists."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.task_routing_accuracy.return_value = {"total_tasks": 0}
        mock_store = MagicMock()

        with (
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            result = cli_automation.cmd_task_routing_report(_args())

        assert result == 0


# ---------------------------------------------------------------------------
# cmd_test_status — plain text fallback (lines 261-273)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdTestStatusPlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_test_status prints plain text when RICH_AVAILABLE is False."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.test_execution_trends.return_value = _test_stats(with_failures=True)
        analytics.coverage_progress.return_value = _coverage_stats()
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

        analytics = MagicMock()
        analytics.test_execution_trends.return_value = _test_stats(with_failures=False)
        analytics.coverage_progress.return_value = _coverage_stats()
        mock_store = MagicMock()

        with (
            patch.object(cli_automation, "RICH_AVAILABLE", False),
            patch("attune.models.telemetry.get_telemetry_store", return_value=mock_store),
            patch("attune.models.telemetry.TelemetryAnalytics", return_value=analytics),
        ):
            cli_automation.cmd_test_status(_args())

        captured = capsys.readouterr()
        assert "Most Frequently" not in captured.out

    def test_exception_returns_early(self, capsys):
        """Exception during analytics is caught and reported."""
        from attune.telemetry import cli_automation

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            side_effect=RuntimeError("unavailable"),
        ):
            cli_automation.cmd_test_status(_args())

        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# cmd_agent_performance — plain text fallback (lines 341-352)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdAgentPerformancePlainText:
    def test_plain_text_output_when_rich_unavailable(self, capsys):
        """cmd_agent_performance prints plain text when RICH_AVAILABLE is False."""
        from attune.telemetry import cli_automation

        analytics = MagicMock()
        analytics.agent_performance.return_value = _agent_stats()
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
