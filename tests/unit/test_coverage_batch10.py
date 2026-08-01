"""Coverage Batch 10 - Comprehensive tests for maximum statement coverage.

Targets modules with low test coverage:
- src/attune/telemetry/cli_analysis.py (~130 uncovered statements, 26% covered)
- src/attune/telemetry/cli_core.py (~108 uncovered statements)
- src/attune/meta_workflows/pattern_learner.py (~110 uncovered statements)
- src/attune/workflows/dependency_check_parsers.py (~98 uncovered statements)

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Module 2: telemetry/cli_analysis.py
# =============================================================================


class TestCmdSonnetOpusAnalysis:
    """Tests for the sonnet/opus fallback analysis CLI command."""

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_no_calls_found(self, capsys: pytest.CaptureFixture) -> None:
        """Test output when no calls are found."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {"total_calls": 0}

        with (
            patch("attune.models.telemetry.get_telemetry_store") as mock_store_fn,
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            mock_store_fn.return_value = MagicMock()
            args = MagicMock()
            args.days = 30
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No Sonnet/Opus calls found" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_plain_text_low_fallback(self, capsys: pytest.CaptureFixture) -> None:
        """Test plain text output with low fallback rate."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 95,
            "success_rate_sonnet": 97.0,
            "opus_fallbacks": 3,
            "fallback_rate": 3.0,
            "actual_cost": 1.50,
            "always_opus_cost": 5.00,
            "savings": 3.50,
            "savings_percent": 70.0,
            "avg_cost_per_call": 0.015,
            "avg_opus_cost_per_call": 0.05,
        }

        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 7
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Excellent" in captured.out
        assert "97.0%" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_plain_text_moderate_fallback(self, capsys: pytest.CaptureFixture) -> None:
        """Test plain text output with moderate fallback rate."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 90,
            "success_rate_sonnet": 88.0,
            "opus_fallbacks": 10,
            "fallback_rate": 10.0,
            "actual_cost": 2.00,
            "always_opus_cost": 5.00,
            "savings": 3.00,
            "savings_percent": 60.0,
            "avg_cost_per_call": 0.02,
            "avg_opus_cost_per_call": 0.05,
        }

        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 30
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Moderate" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_plain_text_high_fallback(self, capsys: pytest.CaptureFixture) -> None:
        """Test plain text output with high fallback rate."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 70,
            "success_rate_sonnet": 60.0,
            "opus_fallbacks": 30,
            "fallback_rate": 30.0,
            "actual_cost": 3.50,
            "always_opus_cost": 5.00,
            "savings": 1.50,
            "savings_percent": 30.0,
            "avg_cost_per_call": 0.035,
            "avg_opus_cost_per_call": 0.05,
        }

        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 30
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "High" in captured.out


class TestCmdFileTestStatus:
    """Tests for the per-file test status CLI command."""

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_no_records(self, capsys: pytest.CaptureFixture) -> None:
        """Test output when no test records exist."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = []

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No per-file test records found" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_specific_file_not_found(self, capsys: pytest.CaptureFixture) -> None:
        """Test output when specific file has no records."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        mock_store = MagicMock()
        mock_store.get_latest_file_test.return_value = None

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = "src/foo.py"
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No test record found" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_plain_text_output_with_records(self, capsys: pytest.CaptureFixture) -> None:
        """Test plain text output with file test records."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        record = MagicMock()
        record.file_path = "src/module.py"
        record.last_test_result = "passed"
        record.is_stale = False
        record.test_count = 5
        record.passed = 5
        record.failed = 0
        record.errors = 0
        record.duration_seconds = 1.2
        record.timestamp = "2026-01-15T10:00:00Z"
        record.failed_tests = []

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = [record]

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "src/module.py" in captured.out
        assert "PASSED" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_plain_text_with_failed_tests(self, capsys: pytest.CaptureFixture) -> None:
        """Test plain text output with failed tests showing details."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        record = MagicMock()
        record.file_path = "src/broken.py"
        record.last_test_result = "failed"
        record.is_stale = True
        record.test_count = 3
        record.passed = 1
        record.failed = 2
        record.errors = 0
        record.duration_seconds = 0.5
        record.timestamp = "2026-01-15T10:00:00Z"
        record.failed_tests = [
            {"name": "test_foo", "error": "AssertionError: expected True"},
        ]

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = [record]

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        assert "[STALE]" in captured.out
        assert "test_foo" in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_failed_filter(self, capsys: pytest.CaptureFixture) -> None:
        """Test that --failed filter only returns failed records."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        passed_record = MagicMock()
        passed_record.file_path = "src/good.py"
        passed_record.last_test_result = "passed"
        passed_record.timestamp = "2026-01-15T10:00:00Z"
        passed_record.is_stale = False

        failed_record = MagicMock()
        failed_record.file_path = "src/bad.py"
        failed_record.last_test_result = "failed"
        failed_record.timestamp = "2026-01-15T10:00:01Z"
        failed_record.is_stale = False
        failed_record.test_count = 1
        failed_record.passed = 0
        failed_record.failed = 1
        failed_record.errors = 0
        failed_record.duration_seconds = 0.1
        failed_record.failed_tests = []

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = [passed_record, failed_record]

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = True
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "src/bad.py" in captured.out
        assert "src/good.py" not in captured.out

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", False)
    def test_empty_after_filter(self, capsys: pytest.CaptureFixture) -> None:
        """Test message when filter produces no results."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        record = MagicMock()
        record.file_path = "src/good.py"
        record.last_test_result = "passed"
        record.timestamp = "2026-01-15T10:00:00Z"
        record.is_stale = False

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = [record]

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = True
            args.stale = True
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No failed and stale" in captured.out

    def test_store_error_returns_1(self, capsys: pytest.CaptureFixture) -> None:
        """Test that store errors are caught and return exit code 1."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            side_effect=RuntimeError("DB error"),
        ):
            args = MagicMock()
            args.file = None
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error retrieving" in captured.out


class TestCmdSonnetOpusAnalysisRich:
    """Tests for sonnet/opus analysis with Rich available."""

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_analysis.Console")
    def test_rich_low_fallback(
        self,
        mock_console_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test Rich output with low fallback rate (<5%)."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 98,
            "success_rate_sonnet": 98.0,
            "opus_fallbacks": 2,
            "fallback_rate": 2.0,
            "actual_cost": 1.00,
            "always_opus_cost": 5.00,
            "savings": 4.00,
            "savings_percent": 80.0,
            "avg_cost_per_call": 0.01,
            "avg_opus_cost_per_call": 0.05,
        }
        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 7
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        # Rich console should have been used
        assert mock_console.print.called

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_analysis.Console")
    def test_rich_moderate_fallback(
        self,
        mock_console_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test Rich output with moderate fallback rate (5-15%)."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 90,
            "success_rate_sonnet": 88.0,
            "opus_fallbacks": 10,
            "fallback_rate": 10.0,
            "actual_cost": 2.00,
            "always_opus_cost": 5.00,
            "savings": 3.00,
            "savings_percent": 60.0,
            "avg_cost_per_call": 0.02,
            "avg_opus_cost_per_call": 0.05,
        }
        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 7
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        assert mock_console.print.called

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_analysis.Console")
    def test_rich_high_fallback(
        self,
        mock_console_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test Rich output with high fallback rate (>15%)."""
        from attune.telemetry.cli_analysis import cmd_sonnet_opus_analysis

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        stats = {
            "total_calls": 100,
            "sonnet_attempts": 70,
            "success_rate_sonnet": 60.0,
            "opus_fallbacks": 30,
            "fallback_rate": 30.0,
            "actual_cost": 3.50,
            "always_opus_cost": 5.00,
            "savings": 1.50,
            "savings_percent": 30.0,
            "avg_cost_per_call": 0.035,
            "avg_opus_cost_per_call": 0.05,
        }
        mock_analytics = MagicMock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = stats

        with (
            patch("attune.models.telemetry.get_telemetry_store"),
            patch(
                "attune.models.telemetry.TelemetryAnalytics",
                return_value=mock_analytics,
            ),
        ):
            args = MagicMock()
            args.days = 7
            result = cmd_sonnet_opus_analysis(args)

        assert result == 0
        assert mock_console.print.called


class TestCmdFileTestStatusRich:
    """Tests for file test status with Rich available."""

    @patch("attune.telemetry.cli_analysis.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_analysis.Console")
    def test_rich_output_with_records(self, mock_console_cls: MagicMock) -> None:
        """Test Rich output with file test records including failed."""
        from attune.telemetry.cli_analysis import cmd_file_test_status

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        record_passed = MagicMock()
        record_passed.file_path = "src/good.py"
        record_passed.last_test_result = "passed"
        record_passed.is_stale = False
        record_passed.test_count = 5
        record_passed.passed = 5
        record_passed.failed = 0
        record_passed.errors = 0
        record_passed.duration_seconds = 1.0
        record_passed.timestamp = "2026-01-15T10:00:00Z"
        record_passed.failed_tests = []

        record_failed = MagicMock()
        record_failed.file_path = "src/bad.py"
        record_failed.last_test_result = "failed"
        record_failed.is_stale = True
        record_failed.test_count = 3
        record_failed.passed = 1
        record_failed.failed = 2
        record_failed.errors = 0
        record_failed.duration_seconds = None
        record_failed.timestamp = "2026-01-15T10:01:00Z"
        record_failed.failed_tests = [
            {"name": "test_broken", "error": "AssertionError: expected True"},
        ]

        record_no_tests = MagicMock()
        record_no_tests.file_path = "src/untested.py"
        record_no_tests.last_test_result = "no_tests"
        record_no_tests.is_stale = False
        record_no_tests.test_count = 0
        record_no_tests.passed = 0
        record_no_tests.failed = 0
        record_no_tests.errors = 0
        record_no_tests.duration_seconds = 0
        record_no_tests.timestamp = "2026-01-15T10:02:00Z"
        record_no_tests.failed_tests = []

        record_unknown = MagicMock()
        record_unknown.file_path = "src/unknown.py"
        record_unknown.last_test_result = "skipped"
        record_unknown.is_stale = False
        record_unknown.test_count = 0
        record_unknown.passed = 0
        record_unknown.failed = 0
        record_unknown.errors = 0
        record_unknown.duration_seconds = 0
        record_unknown.timestamp = "bad-timestamp"
        record_unknown.failed_tests = []

        mock_store = MagicMock()
        mock_store.get_file_tests.return_value = [
            record_passed,
            record_failed,
            record_no_tests,
            record_unknown,
        ]

        with patch(
            "attune.models.telemetry.get_telemetry_store",
            return_value=mock_store,
        ):
            args = MagicMock()
            args.file = None
            args.failed = False
            args.stale = False
            args.limit = 50
            result = cmd_file_test_status(args)

        assert result == 0
        assert mock_console.print.called


# =============================================================================
# Module 3: telemetry/cli_core.py
# =============================================================================


class TestCmdTelemetryShow:
    """Tests for the telemetry show command."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_no_entries(self, mock_tracker_cls: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test output when no telemetry data exists."""
        from attune.telemetry.cli_core import cmd_telemetry_show

        mock_tracker = MagicMock()
        mock_tracker.get_recent_entries.return_value = []
        mock_tracker.telemetry_dir = Path("/tmp/telemetry")
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.limit = 20
        args.days = None
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_plain_text_entries(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test plain text output with telemetry entries."""
        from attune.telemetry.cli_core import cmd_telemetry_show

        mock_tracker = MagicMock()
        mock_tracker.get_recent_entries.return_value = [
            {
                "ts": "2026-01-15T10:00:00Z",
                "workflow": "code-review",
                "stage": "analyze",
                "tier": "cheap",
                "cost": 0.005,
                "tokens": {"input": 1000, "output": 500},
                "cache": {"hit": True, "type": "exact"},
                "duration_ms": 1200,
            },
            {
                "ts": "2026-01-15T10:01:00Z",
                "workflow": "test-gen",
                "stage": "generate",
                "tier": "capable",
                "cost": 0.015,
                "tokens": {"input": 2000, "output": 1000},
                "cache": {"hit": False},
                "duration_ms": 2500,
            },
        ]
        mock_tracker.telemetry_dir = Path("/tmp/telemetry")
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.limit = 20
        args.days = None
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "code-review" in captured.out
        assert "test-gen" in captured.out
        assert "Total Cost:" in captured.out


class TestCmdTelemetrySavings:
    """Tests for the telemetry savings command."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_no_data(self, mock_tracker_cls: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test output when no telemetry data for savings."""
        from attune.telemetry.cli_core import cmd_telemetry_savings

        mock_tracker = MagicMock()
        mock_tracker.calculate_savings.return_value = {"total_calls": 0}
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 30
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_plain_text_savings(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test plain text savings output."""
        from attune.telemetry.cli_core import cmd_telemetry_savings

        mock_tracker = MagicMock()
        mock_tracker.calculate_savings.return_value = {
            "total_calls": 50,
            "tier_distribution": {"cheap": 60.0, "capable": 30.0, "premium": 10.0},
            "baseline_cost": 10.00,
            "actual_cost": 3.50,
            "savings": 6.50,
            "savings_percent": 65.0,
            "cache_savings": 1.20,
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 30
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "COST SAVINGS ANALYSIS" in captured.out
        assert "65.0%" in captured.out
        assert "$6.50" in captured.out


class TestCmdTelemetryCacheStats:
    """Tests for the telemetry cache-stats command."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_no_data(self, mock_tracker_cls: MagicMock, capsys: pytest.CaptureFixture) -> None:
        """Test output when no cache data exists."""
        from attune.telemetry.cli_core import cmd_telemetry_cache_stats

        mock_tracker = MagicMock()
        mock_tracker.get_cache_stats.return_value = {"total_requests": 0}
        mock_tracker.telemetry_dir = Path("/tmp/telemetry")
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 7
        result = cmd_telemetry_cache_stats(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_plain_text_cache_stats(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test plain text cache stats output."""
        from attune.telemetry.cli_core import cmd_telemetry_cache_stats

        mock_tracker = MagicMock()
        mock_tracker.get_cache_stats.return_value = {
            "total_requests": 100,
            "hit_rate": 0.65,
            "total_reads": 50000,
            "total_writes": 20000,
            "savings": 2.50,
            "hit_count": 65,
            "by_workflow": {},
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 7
        result = cmd_telemetry_cache_stats(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "PROMPT CACHING STATS" in captured.out
        assert "65.0%" in captured.out

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_low_hit_rate_recommendation(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test recommendations appear when cache hit rate is low."""
        from attune.telemetry.cli_core import cmd_telemetry_cache_stats

        mock_tracker = MagicMock()
        mock_tracker.get_cache_stats.return_value = {
            "total_requests": 100,
            "hit_rate": 0.10,
            "total_reads": 5000,
            "total_writes": 50000,
            "savings": 0.50,
            "hit_count": 10,
            "by_workflow": {},
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 7
        result = cmd_telemetry_cache_stats(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "low" in captured.out
        assert "Recommendations" in captured.out


class TestCmdTelemetryCompare:
    """Tests for the telemetry compare command."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_insufficient_data(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test output when insufficient data for comparison."""
        from attune.telemetry.cli_core import cmd_telemetry_compare

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"total_calls": 0, "total_cost": 0}
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.period1 = 7
        args.period2 = 30
        result = cmd_telemetry_compare(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Insufficient" in captured.out

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", False)
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_plain_text_comparison(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test plain text comparison output."""
        from attune.telemetry.cli_core import cmd_telemetry_compare

        mock_tracker = MagicMock()
        mock_tracker.get_stats.side_effect = [
            {"total_calls": 50, "total_cost": 2.50, "cache_hit_rate": 60.0},
            {"total_calls": 200, "total_cost": 10.00, "cache_hit_rate": 55.0},
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.period1 = 7
        args.period2 = 30
        result = cmd_telemetry_compare(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "TELEMETRY COMPARISON" in captured.out
        assert "Total Calls" in captured.out


class TestCmdTelemetryReset:
    """Tests for the telemetry reset command."""

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_reset_no_confirm(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test reset without --confirm shows warning."""
        from attune.telemetry.cli_core import cmd_telemetry_reset

        mock_tracker = MagicMock()
        mock_tracker.telemetry_dir = Path("/tmp/telemetry")
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.confirm = False
        result = cmd_telemetry_reset(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_reset_confirmed(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test reset with --confirm deletes data."""
        from attune.telemetry.cli_core import cmd_telemetry_reset

        mock_tracker = MagicMock()
        mock_tracker.reset.return_value = 42
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.confirm = True
        result = cmd_telemetry_reset(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Deleted 42" in captured.out


class TestCmdTelemetryExport:
    """Tests for the telemetry export command."""

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_no_data(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test export when no data exists."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = []
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "json"
        args.output = None
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data" in captured.out

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_json_stdout(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test JSON export to stdout."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = [
            {"ts": "2026-01-01", "workflow": "test", "cost": 0.01},
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "json"
        args.output = None
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data[0]["workflow"] == "test"

    @patch("attune.telemetry.cli_core._validate_file_path")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_json_file(
        self,
        mock_tracker_cls: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test JSON export to file."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        output_file = tmp_path / "export.json"
        mock_validate.return_value = output_file

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = [
            {"ts": "2026-01-01", "workflow": "test", "cost": 0.01},
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "json"
        args.output = str(output_file)
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data[0]["workflow"] == "test"

    @patch("attune.telemetry.cli_core._validate_file_path")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_csv_file(
        self,
        mock_tracker_cls: MagicMock,
        mock_validate: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test CSV export to file."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        output_file = tmp_path / "export.csv"
        mock_validate.return_value = output_file

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = [
            {
                "ts": "2026-01-01",
                "workflow": "test",
                "stage": "analyze",
                "tier": "cheap",
                "model": "claude-3-haiku",
                "provider": "anthropic",
                "cost": 0.005,
                "tokens": {"input": 100, "output": 50},
                "cache": {"hit": False, "type": ""},
                "duration_ms": 500,
            },
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "csv"
        args.output = str(output_file)
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "ts" in content
        assert "test" in content

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_csv_stdout(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test CSV export to stdout."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = [
            {
                "ts": "2026-01-01",
                "workflow": "test",
                "stage": "review",
                "tier": "capable",
                "model": "claude-3-sonnet",
                "provider": "anthropic",
                "cost": 0.01,
                "tokens": {"input": 200, "output": 100},
                "cache": {"hit": True, "type": "exact"},
                "duration_ms": 800,
            },
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "csv"
        args.output = None
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "ts" in captured.out
        assert "test" in captured.out

    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_export_unknown_format(
        self,
        mock_tracker_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test export with unsupported format returns error."""
        from attune.telemetry.cli_core import cmd_telemetry_export

        mock_tracker = MagicMock()
        mock_tracker.export_to_dict.return_value = [{"ts": "2026-01-01"}]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.format = "xml"
        args.output = None
        args.days = None
        result = cmd_telemetry_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown format" in captured.out


class TestCmdTelemetryShowRich:
    """Tests for telemetry show with Rich available."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_core.Console")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_rich_show_entries(
        self,
        mock_tracker_cls: MagicMock,
        mock_console_cls: MagicMock,
    ) -> None:
        """Test Rich output for telemetry show with entries."""
        from attune.telemetry.cli_core import cmd_telemetry_show

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_tracker = MagicMock()
        mock_tracker.get_recent_entries.return_value = [
            {
                "ts": "2026-01-15T10:00:00Z",
                "workflow": "code-review",
                "stage": "analyze",
                "tier": "cheap",
                "cost": 0.005,
                "tokens": {"input": 1000, "output": 500},
                "cache": {"hit": True, "type": "exact"},
                "duration_ms": 1200,
            },
        ]
        mock_tracker.telemetry_dir = Path("/tmp/telemetry")
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.limit = 20
        args.days = None
        result = cmd_telemetry_show(args)

        assert result == 0
        assert mock_console.print.called


class TestCmdTelemetrySavingsRich:
    """Tests for telemetry savings with Rich available."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_core.Console")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_rich_savings(
        self,
        mock_tracker_cls: MagicMock,
        mock_console_cls: MagicMock,
    ) -> None:
        """Test Rich output for savings analysis."""
        from attune.telemetry.cli_core import cmd_telemetry_savings

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_tracker = MagicMock()
        mock_tracker.calculate_savings.return_value = {
            "total_calls": 50,
            "tier_distribution": {"cheap": 60.0, "capable": 30.0, "premium": 10.0},
            "baseline_cost": 10.00,
            "actual_cost": 3.50,
            "savings": 6.50,
            "savings_percent": 65.0,
            "cache_savings": 1.20,
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 30
        result = cmd_telemetry_savings(args)

        assert result == 0
        assert mock_console.print.called


class TestCmdTelemetryCacheStatsRich:
    """Tests for telemetry cache-stats with Rich available."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_core.Console")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_rich_cache_stats_with_workflows(
        self,
        mock_tracker_cls: MagicMock,
        mock_console_cls: MagicMock,
    ) -> None:
        """Test Rich output for cache stats including per-workflow breakdown."""
        from attune.telemetry.cli_core import cmd_telemetry_cache_stats

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_tracker = MagicMock()
        mock_tracker.get_cache_stats.return_value = {
            "total_requests": 100,
            "hit_rate": 0.65,
            "total_reads": 50000,
            "total_writes": 20000,
            "savings": 2.50,
            "hit_count": 65,
            "by_workflow": {
                "code-review": {"hit_rate": 0.8, "reads": 30000, "writes": 10000},
                "test-gen": {"hit_rate": 0.3, "reads": 20000, "writes": 10000},
            },
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 7
        result = cmd_telemetry_cache_stats(args)

        assert result == 0
        assert mock_console.print.called

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_core.Console")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_rich_low_hit_rate_recommendations(
        self,
        mock_tracker_cls: MagicMock,
        mock_console_cls: MagicMock,
    ) -> None:
        """Test Rich output shows recommendations for low cache hit rate."""
        from attune.telemetry.cli_core import cmd_telemetry_cache_stats

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_tracker = MagicMock()
        mock_tracker.get_cache_stats.return_value = {
            "total_requests": 100,
            "hit_rate": 0.10,
            "total_reads": 5000,
            "total_writes": 50000,
            "savings": 0.50,
            "hit_count": 10,
            "by_workflow": {},
        }
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.days = 7
        result = cmd_telemetry_cache_stats(args)

        assert result == 0
        assert mock_console.print.called


class TestCmdTelemetryCompareRich:
    """Tests for telemetry compare with Rich available."""

    @patch("attune.telemetry.cli_core.RICH_AVAILABLE", True)
    @patch("attune.telemetry.cli_core.Console")
    @patch("attune.telemetry.cli_core.UsageTracker")
    def test_rich_comparison(
        self,
        mock_tracker_cls: MagicMock,
        mock_console_cls: MagicMock,
    ) -> None:
        """Test Rich output for telemetry comparison."""
        from attune.telemetry.cli_core import cmd_telemetry_compare

        mock_console = MagicMock()
        mock_console_cls.return_value = mock_console

        mock_tracker = MagicMock()
        mock_tracker.get_stats.side_effect = [
            {"total_calls": 50, "total_cost": 2.50, "cache_hit_rate": 60.0},
            {"total_calls": 200, "total_cost": 10.00, "cache_hit_rate": 55.0},
        ]
        mock_tracker_cls.get_instance.return_value = mock_tracker

        args = MagicMock()
        args.period1 = 7
        args.period2 = 30
        result = cmd_telemetry_compare(args)

        assert result == 0
        assert mock_console.print.called


# =============================================================================
# Module 4: meta_workflows/pattern_learner.py
# =============================================================================


def _make_mock_result(
    run_id: str = "run-001",
    template_id: str = "template-1",
    success: bool = True,
    total_cost: float = 0.10,
    total_duration: float = 5.0,
    agents_created: int = 2,
    agent_results: list | None = None,
) -> MagicMock:
    """Create a mock MetaWorkflowResult for testing.

    Args:
        run_id: Unique run identifier.
        template_id: Template identifier.
        success: Whether the workflow succeeded.
        total_cost: Total cost of the workflow.
        total_duration: Total duration in seconds.
        agents_created: Number of agents created.
        agent_results: List of mock agent results.

    Returns:
        MagicMock configured as a MetaWorkflowResult.

    """
    result = MagicMock()
    result.run_id = run_id
    result.template_id = template_id
    result.success = success
    result.total_cost = total_cost
    result.total_duration = total_duration
    result.agents_created = [MagicMock() for _ in range(agents_created)]
    result.timestamp = "2026-01-15T10:00:00"
    result.error = None

    if agent_results is None:
        ar1 = MagicMock()
        ar1.role = "analyzer"
        ar1.tier_used = "cheap"
        ar1.success = True
        ar1.cost = 0.03

        ar2 = MagicMock()
        ar2.role = "reviewer"
        ar2.tier_used = "capable"
        ar2.success = True
        ar2.cost = 0.07

        result.agent_results = [ar1, ar2]
    else:
        result.agent_results = agent_results

    # For store_execution_in_memory
    form_resp = MagicMock()
    form_resp.responses = {"test_q": "test_a"}
    result.form_responses = form_resp

    # For to_json
    result.to_json.return_value = json.dumps({"run_id": run_id, "template_id": template_id})

    return result


class TestPatternLearnerInit:
    """Tests for PatternLearner initialization."""

    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_default_init(self, mock_list: MagicMock) -> None:
        """Test default initialization uses home directory."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        learner = PatternLearner()
        assert "meta_workflows" in str(learner.executions_dir)
        assert learner.memory is None

    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_custom_dir_and_memory(self, mock_list: MagicMock) -> None:
        """Test initialization with custom directory and memory."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        learner = PatternLearner(
            executions_dir="/tmp/test_executions",
            memory=mock_memory,
        )
        assert learner.executions_dir == Path("/tmp/test_executions")
        assert learner.memory is mock_memory


class TestPatternLearnerAnalyzePatterns:
    """Tests for the analyze_patterns method."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_no_results_returns_empty(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test analyze_patterns returns empty list when no results exist."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = []
        learner = PatternLearner(executions_dir="/tmp/test")

        insights = learner.analyze_patterns()
        assert insights == []

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_analyze_generates_insights(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test analyze_patterns generates insights from results."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001", "run-002", "run-003"]
        mock_load.side_effect = [
            _make_mock_result(run_id="run-001", total_cost=0.10),
            _make_mock_result(run_id="run-002", total_cost=0.15),
            _make_mock_result(run_id="run-003", total_cost=0.20),
        ]

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(min_confidence=0.0)

        assert len(insights) > 0
        insight_types = {i.insight_type for i in insights}
        assert "agent_count" in insight_types
        assert "cost_analysis" in insight_types

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_analyze_with_template_filter(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test analyze_patterns filters by template_id."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001", "run-002"]
        r1 = _make_mock_result(run_id="run-001", template_id="template-a")
        r2 = _make_mock_result(run_id="run-002", template_id="template-b")
        mock_load.side_effect = [r1, r2]

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(template_id="template-a", min_confidence=0.0)

        # Only insights from template-a's data should be included
        assert len(insights) > 0

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_analyze_confidence_filter(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test that high min_confidence filters out low-confidence insights."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        # Only 1 result = confidence 0.1 (1/10)
        mock_list.return_value = ["run-001"]
        mock_load.return_value = _make_mock_result()

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(min_confidence=0.9)

        # All insights should have low confidence with 1 sample
        assert len(insights) == 0

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_analyze_handles_load_error(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test that load errors are logged and skipped."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001", "run-002"]
        mock_load.side_effect = [
            RuntimeError("corrupt file"),
            _make_mock_result(run_id="run-002"),
        ]

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(min_confidence=0.0)

        # Should still produce insights from run-002
        assert len(insights) > 0


class TestPatternLearnerAnalyzeFailures:
    """Tests for the _analyze_failures method."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_failure_insight_generated(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test that failure analysis generates insights for failing agents."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        ar_fail = MagicMock()
        ar_fail.role = "test-agent"
        ar_fail.tier_used = "cheap"
        ar_fail.success = False
        ar_fail.cost = 0.01

        ar_pass = MagicMock()
        ar_pass.role = "test-agent"
        ar_pass.tier_used = "cheap"
        ar_pass.success = True
        ar_pass.cost = 0.02

        mock_list.return_value = ["run-001"]
        result = _make_mock_result(agent_results=[ar_fail, ar_pass])
        mock_load.return_value = result

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(min_confidence=0.0)

        failure_insights = [i for i in insights if i.insight_type == "failure_analysis"]
        assert len(failure_insights) >= 1
        assert failure_insights[0].data["failure_rate"] == 0.5


class TestPatternLearnerTierPerformance:
    """Tests for the _analyze_tier_performance method."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_tier_performance_with_enough_samples(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test tier performance insights require minimum 3 samples."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        # Create 3 results with same agent role/tier
        ar = MagicMock()
        ar.role = "analyzer"
        ar.tier_used = "cheap"
        ar.success = True
        ar.cost = 0.05

        results = []
        for i in range(3):
            r = _make_mock_result(run_id=f"run-{i}", agent_results=[ar])
            results.append(r)

        mock_list.return_value = [f"run-{i}" for i in range(3)]
        mock_load.side_effect = results

        learner = PatternLearner(executions_dir="/tmp/test")
        insights = learner.analyze_patterns(min_confidence=0.0)

        tier_insights = [i for i in insights if i.insight_type == "tier_performance"]
        assert len(tier_insights) >= 1


class TestPatternLearnerRecommendations:
    """Tests for the get_recommendations method."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_recommendations_from_insights(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test get_recommendations produces actionable text."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        # 3 runs with mixed success for tier_performance
        ar_good = MagicMock()
        ar_good.role = "analyzer"
        ar_good.tier_used = "cheap"
        ar_good.success = True
        ar_good.cost = 0.03

        ar_bad = MagicMock()
        ar_bad.role = "reviewer"
        ar_bad.tier_used = "cheap"
        ar_bad.success = False
        ar_bad.cost = 0.02

        results = []
        for i in range(5):
            r = _make_mock_result(
                run_id=f"run-{i}",
                template_id="tmpl-x",
                agent_results=[ar_good, ar_bad],
            )
            results.append(r)

        mock_list.return_value = [f"run-{i}" for i in range(5)]
        mock_load.side_effect = results

        learner = PatternLearner(executions_dir="/tmp/test")
        recs = learner.get_recommendations("tmpl-x", min_confidence=0.0)

        assert isinstance(recs, list)
        # Should have at least cost recommendation
        cost_recs = [r for r in recs if "$" in r]
        assert len(cost_recs) >= 1


class TestPatternLearnerAnalyticsReport:
    """Tests for the generate_analytics_report method."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_analytics_report_structure(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test that analytics report has expected structure."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001"]
        mock_load.return_value = _make_mock_result()

        learner = PatternLearner(executions_dir="/tmp/test")
        report = learner.generate_analytics_report()

        assert "summary" in report
        assert "insights" in report
        assert "recommendations" in report
        assert report["summary"]["total_runs"] == 1


class TestPatternLearnerMemoryIntegration:
    """Tests for memory-based storage and search."""

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_store_execution_no_memory(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test store_execution_in_memory returns None when no memory."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        learner = PatternLearner(executions_dir="/tmp/test")
        result = learner.store_execution_in_memory(_make_mock_result())
        assert result is None

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_store_execution_with_memory(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test store_execution_in_memory stores to memory and returns pattern_id."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        mock_memory.persist_pattern.return_value = {"pattern_id": "pat-123"}

        learner = PatternLearner(executions_dir="/tmp/test", memory=mock_memory)
        result = learner.store_execution_in_memory(_make_mock_result())

        assert result == "pat-123"
        mock_memory.persist_pattern.assert_called_once()

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_store_execution_memory_error(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test store_execution_in_memory handles memory errors gracefully."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        mock_memory.persist_pattern.side_effect = RuntimeError("memory error")

        learner = PatternLearner(executions_dir="/tmp/test", memory=mock_memory)
        result = learner.store_execution_in_memory(_make_mock_result())

        assert result is None

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_search_no_memory_uses_file_fallback(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test search falls back to file-based when no memory available."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001"]
        r = _make_mock_result()
        mock_load.return_value = r

        learner = PatternLearner(executions_dir="/tmp/test")
        results = learner.search_executions_by_context("test query")

        # File-based search should have been attempted
        assert isinstance(results, list)

    @patch("attune.meta_workflows.pattern_memory.load_execution_result")
    @patch("attune.meta_workflows.pattern_memory.list_execution_results")
    def test_search_with_memory(self, mock_list: MagicMock, mock_load: MagicMock) -> None:
        """Test search via memory with results."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        mock_memory.search_patterns.return_value = [
            {"metadata": {"run_id": "run-001", "template_id": "tmpl-1"}},
        ]

        r = _make_mock_result(run_id="run-001")
        mock_load.return_value = r

        learner = PatternLearner(executions_dir="/tmp/test", memory=mock_memory)
        results = learner.search_executions_by_context("test", template_id="tmpl-1")

        assert len(results) == 1

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_search_memory_error_falls_back(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test search falls back to files when memory search errors."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        mock_memory.search_patterns.side_effect = RuntimeError("search error")

        mock_list.return_value = ["run-001"]
        mock_load.return_value = _make_mock_result()

        learner = PatternLearner(executions_dir="/tmp/test", memory=mock_memory)
        results = learner.search_executions_by_context("query")

        assert isinstance(results, list)

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_smart_recommendations_without_memory(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test get_smart_recommendations without memory returns base recs."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_list.return_value = ["run-001"]
        mock_load.return_value = _make_mock_result()

        learner = PatternLearner(executions_dir="/tmp/test")
        recs = learner.get_smart_recommendations("tmpl-1", min_confidence=0.0)

        assert isinstance(recs, list)

    @patch("attune.meta_workflows.pattern_learner.load_execution_result")
    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_smart_recommendations_with_memory(
        self,
        mock_list: MagicMock,
        mock_load: MagicMock,
    ) -> None:
        """Test get_smart_recommendations with memory enhances base recs."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        mock_memory = MagicMock()
        mock_memory.search_patterns.return_value = [
            {"metadata": {"run_id": "run-001", "template_id": "tmpl-1"}},
        ]

        r = _make_mock_result(success=True)
        mock_list.return_value = ["run-001"]
        mock_load.return_value = r

        form_response = MagicMock()
        form_response.responses = {"q1": "a1", "q2": "a2"}

        learner = PatternLearner(executions_dir="/tmp/test", memory=mock_memory)
        recs = learner.get_smart_recommendations(
            "tmpl-1",
            form_response=form_response,
            min_confidence=0.0,
        )

        assert isinstance(recs, list)


class TestPrintAnalyticsReport:
    """Tests for the print_analytics_report helper function."""

    def test_print_report(self, capsys: pytest.CaptureFixture) -> None:
        """Test that print_analytics_report formats report correctly."""
        from attune.meta_workflows.pattern_learner import print_analytics_report

        report = {
            "summary": {
                "total_runs": 10,
                "successful_runs": 8,
                "success_rate": 0.8,
                "total_cost": 1.50,
                "avg_cost_per_run": 0.15,
                "total_agents_created": 30,
                "avg_agents_per_run": 3.0,
            },
            "recommendations": ["Upgrade tier for reviewer agent"],
            "insights": {
                "tier_performance": [
                    {
                        "description": "analyzer at cheap: 90% success",
                        "confidence": 0.8,
                        "sample_size": 10,
                    },
                ],
                "cost_analysis": [{"description": "Average workflow cost $0.15"}],
                "failure_analysis": [{"description": "reviewer fails 20% of the time"}],
            },
        }

        print_analytics_report(report)
        captured = capsys.readouterr()

        assert "META-WORKFLOW ANALYTICS REPORT" in captured.out
        assert "Total Runs: 10" in captured.out
        assert "Successful: 8 (80%)" in captured.out
        assert "Upgrade tier" in captured.out
        assert "Tier Performance" in captured.out
        assert "Cost Analysis" in captured.out
        assert "Failure Analysis" in captured.out


class TestPatternLearnerFormatHelpers:
    """Tests for _format_agents_for_content and _format_responses_for_content."""

    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_format_agents_for_content(self, mock_list: MagicMock) -> None:
        """Test formatting agent results for memory content."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        learner = PatternLearner(executions_dir="/tmp/test")
        mock_result = _make_mock_result()

        content = learner._format_agents_for_content(mock_result)
        assert "analyzer" in content
        assert "reviewer" in content

    @patch("attune.meta_workflows.pattern_learner.list_execution_results")
    def test_format_responses_for_content(self, mock_list: MagicMock) -> None:
        """Test formatting form responses for memory content."""
        from attune.meta_workflows.pattern_learner import PatternLearner

        learner = PatternLearner(executions_dir="/tmp/test")
        responses = {"project_name": "attune-ai", "version": "2.5.0"}
        content = learner._format_responses_for_content(responses)

        assert "project_name" in content
        assert "attune-ai" in content


# =============================================================================
# Module 5: workflows/dependency_check_parsers.py
# =============================================================================


class TestDependencyParserMixin:
    """Tests for the DependencyParserMixin class."""

    def _make_parser(self) -> Any:
        """Create a parser instance using the mixin."""
        from attune.workflows.dependency_check_parsers import DependencyParserMixin

        class TestParser(DependencyParserMixin):
            """Test class using the mixin."""

        return TestParser()


class TestParseRequirements(TestDependencyParserMixin):
    """Tests for _parse_requirements method."""

    def test_basic_requirements(self, tmp_path: Path) -> None:
        """Test parsing a standard requirements.txt."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28.0\nflask==2.3.0\npytest\n")

        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 3
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert "pytest" in names
        assert all(d["ecosystem"] == "python" for d in deps)

    def test_skips_comments_and_blank_lines(self, tmp_path: Path) -> None:
        """Test that comments and blank lines are skipped."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("# This is a comment\n\nrequests>=2.28.0\n\n# Another comment\n")

        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"

    def test_skips_options_and_urls(self, tmp_path: Path) -> None:
        """Test that -r, -e, and URL lines are skipped."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "-r base.txt\n"
            "-e .\n"
            "https://example.com/pkg.tar.gz\n"
            "http://example.com/pkg.whl\n"
            "./local-pkg\n"
            "/absolute/pkg\n"
            "requests>=2.28.0\n",
        )

        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"

    def test_with_extras(self, tmp_path: Path) -> None:
        """Test parsing requirements with extras."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests[security]>=2.28.0\n")

        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"
        assert "security" in deps[0].get("extras", [])

    @patch("attune.workflows.dependency_check_parsers.logger")
    def test_unreadable_file(self, mock_logger: MagicMock, tmp_path: Path) -> None:
        """Test graceful handling of unreadable files."""
        req_file = tmp_path / "requirements.txt"
        # File does not exist
        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert deps == []

    def test_fallback_parser(self, tmp_path: Path) -> None:
        """Test the fallback parser when packaging is not available."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28.0\nflask\npytest==7.0\n")

        parser = self._make_parser()
        deps = parser._parse_requirements_fallback(req_file)

        assert len(deps) == 3
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert "pytest" in names

    def test_fallback_parser_unreadable(self, tmp_path: Path) -> None:
        """Test fallback parser with nonexistent file."""
        req_file = tmp_path / "nonexistent.txt"

        parser = self._make_parser()
        deps = parser._parse_requirements_fallback(req_file)

        assert deps == []


class TestParsePyproject(TestDependencyParserMixin):
    """Tests for _parse_pyproject method."""

    def test_pep621_dependencies(self, tmp_path: Path) -> None:
        """Test parsing PEP 621 style dependencies from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [project]
            name = "my-package"
            dependencies = [
                "requests>=2.28.0",
                "flask==2.3.0",
            ]
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names

    def test_poetry_dependencies(self, tmp_path: Path) -> None:
        """Test parsing Poetry style dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [tool.poetry.dependencies]
            python = "^3.10"
            requests = "^2.28.0"
            flask = {version = "^2.3.0"}

            [tool.poetry.dev-dependencies]
            pytest = "^7.0"
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert "pytest" in names
        # Python itself should be skipped
        assert "python" not in names

        # Check dev dependency flagged
        pytest_dep = [d for d in deps if d["name"] == "pytest"][0]
        assert pytest_dep.get("dev") is True

    def test_poetry_deps_dict_spec(self, tmp_path: Path) -> None:
        """Test Poetry deps with dict spec (like extras or git)."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [tool.poetry.dependencies]
            python = "^3.10"
            my-lib = {version = "^1.0", extras = ["all"]}
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        names = [d["name"] for d in deps]
        assert "my-lib" in names

    def test_pyproject_fallback(self, tmp_path: Path) -> None:
        """Test the fallback TOML parser."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [project]
            dependencies = [
                "requests>=2.28.0",
                "flask==2.3.0",
            ]
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject_fallback(pyproject)

        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names

    def test_pyproject_fallback_unreadable(self, tmp_path: Path) -> None:
        """Test fallback parser with nonexistent file."""
        pyproject = tmp_path / "nonexistent.toml"
        parser = self._make_parser()
        deps = parser._parse_pyproject_fallback(pyproject)
        assert deps == []


class TestParsePackageJson(TestDependencyParserMixin):
    """Tests for _parse_package_json method."""

    def test_basic_package_json(self, tmp_path: Path) -> None:
        """Test parsing package.json with both dep types."""
        pkg = tmp_path / "package.json"
        pkg.write_text(
            json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {
                        "express": "^4.18.0",
                        "lodash": "~4.17.21",
                    },
                    "devDependencies": {
                        "jest": "^29.0.0",
                    },
                },
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_package_json(pkg)

        assert len(deps) == 3
        names = [d["name"] for d in deps]
        assert "express" in names
        assert "lodash" in names
        assert "jest" in names
        assert all(d["ecosystem"] == "node" for d in deps)

        jest_dep = [d for d in deps if d["name"] == "jest"][0]
        assert jest_dep["dev"] is True

    def test_empty_package_json(self, tmp_path: Path) -> None:
        """Test parsing package.json with no dependencies."""
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "empty-app"}))

        parser = self._make_parser()
        deps = parser._parse_package_json(pkg)

        assert deps == []

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Test graceful handling of invalid JSON."""
        pkg = tmp_path / "package.json"
        pkg.write_text("{invalid json")

        parser = self._make_parser()
        deps = parser._parse_package_json(pkg)

        assert deps == []

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test graceful handling of nonexistent file."""
        parser = self._make_parser()
        deps = parser._parse_package_json(tmp_path / "nope.json")
        assert deps == []


class TestParsePoetryLock(TestDependencyParserMixin):
    """Tests for _parse_poetry_lock method."""

    def test_basic_poetry_lock(self, tmp_path: Path) -> None:
        """Test parsing poetry.lock with pinned versions."""
        lock_file = tmp_path / "poetry.lock"
        lock_file.write_text(
            textwrap.dedent(
                """\
            [[package]]
            name = "requests"
            version = "2.28.2"

            [[package]]
            name = "flask"
            version = "2.3.0"
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_poetry_lock(lock_file)

        assert len(deps) == 2
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert all(d["pinned"] is True for d in deps)
        assert deps[0]["version"].startswith("==")

    def test_poetry_lock_no_tomllib(self, tmp_path: Path, monkeypatch) -> None:
        """Test poetry.lock parsing when tomllib is not available."""
        self._make_parser()
        lock_file = tmp_path / "poetry.lock"
        lock_file.write_text("[[package]]\nname = 'x'\nversion = '1.0'\n")

        # monkeypatch.setitem, not patch.dict("sys.modules", ...) — the
        # latter's clear+rebuild teardown races under xdist (guard test).
        monkeypatch.setitem(sys.modules, "tomllib", None)
        monkeypatch.setitem(sys.modules, "tomli", None)
        # Re-import to get fresh behavior
        import importlib

        import attune.workflows.dependency_check_parsers as mod

        importlib.reload(mod)

        class TestParser(mod.DependencyParserMixin):
            """Test parser."""

        p = TestParser()
        deps = p._parse_poetry_lock(lock_file)
        # Should return empty since tomllib is not available
        assert deps == []


class TestParsePackageLockJson(TestDependencyParserMixin):
    """Tests for _parse_package_lock_json method."""

    def test_npm_v7_format(self, tmp_path: Path) -> None:
        """Test parsing npm v7+ package-lock.json format."""
        lock_file = tmp_path / "package-lock.json"
        lock_file.write_text(
            json.dumps(
                {
                    "packages": {
                        "": {"name": "root", "version": "1.0.0"},
                        "node_modules/express": {"version": "4.18.2"},
                        "node_modules/lodash": {"version": "4.17.21"},
                    },
                },
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_package_lock_json(lock_file)

        assert len(deps) == 2
        names = [d["name"] for d in deps]
        assert "express" in names
        assert "lodash" in names
        assert all(d["pinned"] is True for d in deps)

    def test_npm_v6_format(self, tmp_path: Path) -> None:
        """Test parsing npm v6 package-lock.json format."""
        lock_file = tmp_path / "package-lock.json"
        lock_file.write_text(
            json.dumps(
                {
                    "dependencies": {
                        "express": {"version": "4.18.2"},
                        "lodash": {"version": "4.17.21"},
                    },
                },
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_package_lock_json(lock_file)

        assert len(deps) == 2
        names = [d["name"] for d in deps]
        assert "express" in names
        assert "lodash" in names

    def test_invalid_json_lock(self, tmp_path: Path) -> None:
        """Test graceful handling of invalid JSON in package-lock."""
        lock_file = tmp_path / "package-lock.json"
        lock_file.write_text("{bad}")

        parser = self._make_parser()
        deps = parser._parse_package_lock_json(lock_file)

        assert deps == []

    def test_empty_packages_section(self, tmp_path: Path) -> None:
        """Test parsing when packages section has only root entry."""
        lock_file = tmp_path / "package-lock.json"
        lock_file.write_text(
            json.dumps(
                {
                    "packages": {
                        "": {"name": "root", "version": "1.0.0"},
                    },
                },
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_package_lock_json(lock_file)

        assert deps == []


class TestParseRequirementsPackagingUnavailable(TestDependencyParserMixin):
    """Tests for _parse_requirements when the packaging library import fails."""

    def test_packaging_import_error_uses_fallback(self, tmp_path: Path, monkeypatch) -> None:
        """When `packaging.requirements` can't be imported, fall back to regex parsing."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests>=2.28.0\nflask\n")

        parser = self._make_parser()
        monkeypatch.setitem(sys.modules, "packaging.requirements", None)
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 2
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names

    def test_unparseable_requirement_line_skipped(self, tmp_path: Path) -> None:
        """A line that survives the pre-filters but fails Requirement() parsing is skipped."""
        req_file = tmp_path / "requirements.txt"
        # ">=1.0" isn't blank/comment/option/URL/path, so it reaches Requirement()
        # parsing, where it fails (no package name) and must be skipped, not raised.
        req_file.write_text(">=1.0\nrequests>=2.28.0\n")

        parser = self._make_parser()
        deps = parser._parse_requirements(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"


class TestParseRequirementsFallbackSkipping(TestDependencyParserMixin):
    """Tests for comment/blank/option skipping in the fallback requirements parser."""

    def test_fallback_skips_comments_blanks_and_options(self, tmp_path: Path) -> None:
        """Comments, blank lines, and `-e`/`-r` options are skipped without producing deps."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "# a comment\n\n-e .\n-r base.txt\nrequests>=2.28.0\n",
        )

        parser = self._make_parser()
        deps = parser._parse_requirements_fallback(req_file)

        assert len(deps) == 1
        assert deps[0]["name"] == "requests"


class TestParsePyprojectNoTomlLibrary(TestDependencyParserMixin):
    """Tests for _parse_pyproject when neither tomllib nor tomli is importable."""

    def test_tomllib_and_tomli_unavailable_uses_fallback(self, tmp_path: Path, monkeypatch) -> None:
        """Missing both TOML libraries falls back to the regex-based parser."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [project]
            dependencies = [
                "requests>=2.28.0",
            ]
        """,
            ),
        )

        parser = self._make_parser()
        monkeypatch.setitem(sys.modules, "tomllib", None)
        monkeypatch.setitem(sys.modules, "tomli", None)
        deps = parser._parse_pyproject(pyproject)

        names = [d["name"] for d in deps]
        assert "requests" in names


class TestParsePyprojectPackagingUnavailable(TestDependencyParserMixin):
    """Tests for _parse_pyproject when the packaging library is unavailable."""

    def test_packaging_unavailable_uses_regex_extraction(self, tmp_path: Path, monkeypatch) -> None:
        """Without packaging, PEP 621 deps are extracted via a bare-name regex."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [project]
            dependencies = [
                "requests>=2.28.0",
                "flask==2.3.0",
            ]
        """,
            ),
        )

        parser = self._make_parser()
        monkeypatch.setitem(sys.modules, "packaging.requirements", None)
        deps = parser._parse_pyproject(pyproject)

        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "flask" in names
        assert all(d["version"] == "any" for d in deps)


class TestParsePyprojectUnparseableDependency(TestDependencyParserMixin):
    """Tests for the except branch when a PEP 621 dependency string is unparseable."""

    def test_unparseable_dependency_skipped(self, tmp_path: Path) -> None:
        """A malformed PEP 621 dependency string is skipped, not raised."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [project]
            dependencies = [
                ">=bad spec",
            ]
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        assert deps == []


class TestParsePyprojectPoetryDepSpecOtherType(TestDependencyParserMixin):
    """Tests for the else branch when a Poetry dependency spec is neither str nor dict."""

    def test_non_str_non_dict_spec_defaults_to_any(self, tmp_path: Path) -> None:
        """A Poetry dependency spec that's a list (or other type) defaults to version 'any'."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            textwrap.dedent(
                """\
            [tool.poetry.dependencies]
            python = "^3.10"
            weird-dep = [1, 2, 3]
        """,
            ),
        )

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        weird = [d for d in deps if d["name"] == "weird-dep"][0]
        assert weird["version"] == "any"


class TestParsePyprojectMalformedToml(TestDependencyParserMixin):
    """Tests for the broad except branch when pyproject.toml itself fails to parse."""

    def test_malformed_toml_caught_and_returns_empty(self, tmp_path: Path) -> None:
        """Invalid TOML syntax is caught by the broad exception handler, not raised."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not valid toml [[[")

        parser = self._make_parser()
        deps = parser._parse_pyproject(pyproject)

        assert deps == []


class TestParsePoetryLockMalformedToml(TestDependencyParserMixin):
    """Tests for the broad except branch when poetry.lock itself fails to parse."""

    def test_malformed_toml_caught_and_returns_empty(self, tmp_path: Path) -> None:
        """Invalid TOML syntax in poetry.lock is caught, not raised."""
        lock_file = tmp_path / "poetry.lock"
        lock_file.write_text("not valid toml [[[")

        parser = self._make_parser()
        deps = parser._parse_poetry_lock(lock_file)

        assert deps == []
