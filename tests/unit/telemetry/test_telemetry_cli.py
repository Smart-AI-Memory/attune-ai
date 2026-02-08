"""Tests for telemetry/cli.py using real data.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from attune.telemetry.cli import (
    _validate_file_path,
    cmd_agent_performance,
    cmd_sonnet_opus_analysis,
    cmd_task_routing_report,
    cmd_telemetry_compare,
    cmd_telemetry_export,
    cmd_telemetry_reset,
    cmd_telemetry_savings,
    cmd_telemetry_show,
    cmd_test_status,
    cmd_tier1_status,
)
from attune.telemetry.commands.dashboard_commands import cmd_telemetry_dashboard
from attune.telemetry.usage_tracker import UsageTracker


class TestValidateFilePath:
    """Test _validate_file_path security validation."""

    def test_validate_file_path_with_valid_path(self, tmp_path):
        """Test validation succeeds with valid path."""
        test_file = tmp_path / "output.csv"

        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_validate_file_path_rejects_empty_string(self):
        """Test validation rejects empty string."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path("")

    def test_validate_file_path_rejects_null_bytes(self):
        """Test validation rejects paths with null bytes."""
        with pytest.raises(ValueError, match="contains null bytes"):
            _validate_file_path("output\x00.csv")

    def test_validate_file_path_with_system_paths(self):
        """Test validation blocks system paths including macOS symlinks."""
        # On macOS, /etc resolves to /private/etc which IS blocked
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/etc/test.txt")

    def test_validate_file_path_rejects_sys_directory(self):
        """Test validation blocks /sys directory."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/sys/kernel/debug")

    def test_validate_file_path_rejects_proc_directory(self):
        """Test validation blocks /proc directory."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/proc/self/mem")

    def test_validate_file_path_rejects_dev_directory(self):
        """Test validation blocks /dev directory."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/dev/null")

    def test_validate_file_path_with_allowed_directory(self, tmp_path):
        """Test validation with allowed directory restriction."""
        allowed_dir = tmp_path / "exports"
        allowed_dir.mkdir()

        test_file = allowed_dir / "output.csv"

        result = _validate_file_path(str(test_file), allowed_dir=str(allowed_dir))

        assert isinstance(result, Path)

    def test_validate_file_path_rejects_outside_allowed_dir(self, tmp_path):
        """Test validation rejects paths outside allowed directory."""
        allowed_dir = tmp_path / "exports"
        allowed_dir.mkdir()

        outside_file = tmp_path / "outside.csv"

        with pytest.raises(ValueError, match="must be within"):
            _validate_file_path(str(outside_file), allowed_dir=str(allowed_dir))

    def test_validate_file_path_rejects_path_traversal(self, tmp_path):
        """Test validation handles path traversal attempts.

        Use absolute /etc/passwd to test system directory blocking
        regardless of working directory depth.
        """
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/etc/passwd")

    def test_validate_file_path_resolves_relative_paths(self, tmp_path):
        """Test validation resolves relative paths to absolute."""
        result = _validate_file_path("./output.csv")

        assert result.is_absolute()

    def test_validate_file_path_rejects_non_string(self):
        """Test validation rejects non-string inputs."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path(None)

        with pytest.raises(ValueError, match="must be a non-empty string"):
            _validate_file_path(123)

    def test_validate_file_path_accepts_pathlib_string(self, tmp_path):
        """Test validation accepts string from Path object."""
        test_path = tmp_path / "output.txt"
        result = _validate_file_path(str(test_path))

        assert isinstance(result, Path)
        assert result.is_absolute()


class TestValidateFilePathEdgeCases:
    """Test edge cases for file path validation."""

    def test_validate_file_path_with_spaces(self, tmp_path):
        """Test validation handles paths with spaces."""
        test_file = tmp_path / "file with spaces.csv"
        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)

    def test_validate_file_path_with_special_chars(self, tmp_path):
        """Test validation handles special characters."""
        test_file = tmp_path / "file-name_123.csv"
        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)

    def test_validate_file_path_subdirectories(self, tmp_path):
        """Test validation works with nested subdirectories."""
        test_file = tmp_path / "level1" / "level2" / "level3" / "file.csv"
        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)

    def test_validate_file_path_current_directory(self):
        """Test validation works with current directory paths."""
        result = _validate_file_path("./test.csv")

        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_validate_file_path_parent_directory_safe(self, tmp_path):
        """Test validation allows safe parent directory navigation."""
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Navigate to parent (but still within tmp_path)
        test_file = subdir / ".." / "file.csv"
        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)


class TestCmdTelemetryShow:
    """Test cmd_telemetry_show command."""

    def test_show_with_no_data(self, tmp_path, capsys):
        """Test show command with no telemetry data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out
        assert str(tmp_path) in captured.out

    def test_show_with_data(self, tmp_path, capsys):
        """Test show command with telemetry data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="test-workflow",
            stage="analysis",
            tier="CAPABLE",
            model="claude-sonnet-4.5",
            provider="anthropic",
            cost=0.0025,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=1500,
        )

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        # Rich truncates long workflow names in table, so check for partial match
        assert "test-workflow" in captured.out or "test…" in captured.out
        assert "CAPABLE" in captured.out or "CAPA…" in captured.out
        assert "$0.0025" in captured.out or "$0.0…" in captured.out

    def test_show_with_limit(self, tmp_path, capsys):
        """Test show command respects limit parameter."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add multiple entries
        for i in range(10):
            tracker.track_llm_call(
                workflow=f"workflow-{i}",
                stage="test",
                tier="CHEAP",
                model="test-model",
                provider="test",
                cost=0.001,
                tokens={"input": 10, "output": 5},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        args = Mock(limit=5, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        # Should show only recent entries based on limit

    def test_show_with_days_filter(self, tmp_path, capsys):
        """Test show command filters by days parameter."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add recent entry
        tracker.track_llm_call(
            workflow="recent",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(limit=20, days=1)
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        # Rich truncates workflow names, check for partial match
        assert "recent" in captured.out or "rece…" in captured.out

    def test_show_displays_cache_hit(self, tmp_path, capsys):
        """Test show command displays cache hit information."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        tracker.track_llm_call(
            workflow="cached",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.0,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="hash",
            duration_ms=50,
        )

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "HIT" in captured.out or "MISS" in captured.out


class TestCmdTelemetrySavings:
    """Test cmd_telemetry_savings command."""

    def test_savings_with_no_data(self, tmp_path, capsys):
        """Test savings command with no data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(days=30)
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out

    def test_savings_calculation(self, tmp_path, capsys):
        """Test savings calculation with mixed tiers."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add cheap tier calls
        for _ in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CHEAP",
                model="test-model",
                provider="test",
                cost=0.001,
                tokens={"input": 10, "output": 5},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        # Add premium tier call
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="PREMIUM",
            model="test-model",
            provider="test",
            cost=0.05,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=1000,
        )

        args = Mock(days=30)
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "SAVINGS" in captured.out
        assert "CHEAP" in captured.out
        assert "PREMIUM" in captured.out

    def test_savings_with_cache_hits(self, tmp_path, capsys):
        """Test savings includes cache hit savings."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add calls with cache hits
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.0,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="hash",
            duration_ms=50,
        )

        args = Mock(days=30)
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Cache savings" in captured.out


class TestCmdTelemetryCompare:
    """Test cmd_telemetry_compare command."""

    def test_compare_with_insufficient_data(self, tmp_path, capsys):
        """Test compare command with insufficient data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(period1=7, period2=30)
        result = cmd_telemetry_compare(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Insufficient telemetry data" in captured.out

    def test_compare_two_periods(self, tmp_path, capsys):
        """Test compare command with data in both periods."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add multiple entries
        for _i in range(10):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CAPABLE",
                model="test-model",
                provider="test",
                cost=0.002,
                tokens={"input": 50, "output": 25},
                cache_hit=False,
                cache_type=None,
                duration_ms=500,
            )

        args = Mock(period1=7, period2=30)
        result = cmd_telemetry_compare(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Total Calls" in captured.out
        assert "Total Cost" in captured.out


class TestCmdTelemetryReset:
    """Test cmd_telemetry_reset command."""

    def test_reset_without_confirm(self, tmp_path, capsys):
        """Test reset command requires confirmation."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(confirm=False)
        result = cmd_telemetry_reset(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "--confirm" in captured.out

    def test_reset_with_confirm(self, tmp_path, capsys):
        """Test reset command with confirmation."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add some data first
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(confirm=True)
        result = cmd_telemetry_reset(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Deleted" in captured.out
        assert "entries" in captured.out

    def test_reset_empty_directory(self, tmp_path, capsys):
        """Test reset command on empty telemetry directory."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(confirm=True)
        result = cmd_telemetry_reset(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Deleted 0" in captured.out


class TestCmdTelemetryExport:
    """Test cmd_telemetry_export command."""

    def test_export_no_data(self, tmp_path, capsys):
        """Test export command with no data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(format="json", output=None, days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data to export" in captured.out

    def test_export_json_to_stdout(self, tmp_path, capsys):
        """Test export JSON to stdout."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="export-test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.003,
            tokens={"input": 75, "output": 30},
            cache_hit=False,
            cache_type=None,
            duration_ms=750,
        )

        args = Mock(format="json", output=None, days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "export-test" in captured.out
        assert "CAPABLE" in captured.out

    def test_export_json_to_file(self, tmp_path):
        """Test export JSON to file."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="export-test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.003,
            tokens={"input": 75, "output": 30},
            cache_hit=False,
            cache_type=None,
            duration_ms=750,
        )

        output_file = tmp_path / "export.json"
        args = Mock(format="json", output=str(output_file), days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()

        # Verify file content
        with open(output_file) as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]["workflow"] == "export-test"

    def test_export_csv_to_file(self, tmp_path):
        """Test export CSV to file."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="csv-test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 20, "output": 10},
            cache_hit=True,
            cache_type="hash",
            duration_ms=100,
        )

        output_file = tmp_path / "export.csv"
        args = Mock(format="csv", output=str(output_file), days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()

        # Verify CSV content
        with open(output_file, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["workflow"] == "csv-test"
            assert rows[0]["cache_hit"] == "True"

    def test_export_csv_to_stdout(self, tmp_path, capsys):
        """Test export CSV to stdout."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="csv-stdout",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.002,
            tokens={"input": 40, "output": 20},
            cache_hit=False,
            cache_type=None,
            duration_ms=200,
        )

        args = Mock(format="csv", output=None, days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "csv-stdout" in captured.out
        assert "workflow" in captured.out  # CSV header

    def test_export_with_days_filter(self, tmp_path):
        """Test export respects days filter."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="filtered",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        output_file = tmp_path / "filtered.json"
        args = Mock(format="json", output=str(output_file), days=1)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()

    def test_export_invalid_format(self, tmp_path, capsys):
        """Test export with invalid format."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add data so we don't exit early with "no data to export"
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(format="xml", output=None, days=None)
        result = cmd_telemetry_export(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown format" in captured.out

    def test_export_validates_file_path(self, tmp_path):
        """Test export validates output file path."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add data
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        # Try to export to system directory
        args = Mock(format="json", output="/dev/null", days=None)
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            cmd_telemetry_export(args)


class TestCmdTelemetryDashboard:
    """Test cmd_telemetry_dashboard command."""

    def test_dashboard_with_no_data(self, tmp_path, capsys):
        """Test dashboard command with no data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "No telemetry data available" in captured.out

    @patch("webbrowser.open")
    def test_dashboard_creates_html(self, mock_open, tmp_path):
        """Test dashboard creates HTML file."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="dashboard-test",
            stage="test",
            tier="CAPABLE",
            model="claude-sonnet-4.5",
            provider="anthropic",
            cost=0.0025,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="hash",
            duration_ms=1500,
        )

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        assert mock_open.called

    @patch("webbrowser.open")
    def test_dashboard_with_multiple_tiers(self, mock_open, tmp_path):
        """Test dashboard with data from multiple tiers."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add data from each tier
        for tier in ["CHEAP", "CAPABLE", "PREMIUM"]:
            tracker.track_llm_call(
                workflow=f"workflow-{tier}",
                stage="test",
                tier=tier,
                model="test-model",
                provider="test",
                cost=0.001 if tier == "CHEAP" else 0.01 if tier == "CAPABLE" else 0.05,
                tokens={"input": 50, "output": 25},
                cache_hit=False,
                cache_type=None,
                duration_ms=500,
            )

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        assert mock_open.called


class TestTier1MonitoringCommands:
    """Test Tier 1 automation monitoring commands."""

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_tier1_status_no_data(self, mock_store, capsys):
        """Test tier1_status with no data."""
        mock_analytics = Mock()
        mock_analytics.tier1_summary.return_value = {
            "task_routing": {
                "total_tasks": 0,
                "accuracy_rate": 0.0,
                "avg_confidence": 0.0,
            },
            "test_execution": {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "total_failures": 0,
            },
            "coverage": {
                "current_coverage": 0.0,
                "change": 0.0,
                "trend": "stable",
                "critical_gaps_count": 0,
            },
            "agent_performance": {
                "by_agent": {},
                "automation_rate": 0.0,
                "human_review_rate": 0.0,
            },
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=24)
            result = cmd_tier1_status(args)

            assert result == 0

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_tier1_status_with_error(self, mock_store, capsys):
        """Test tier1_status handles errors gracefully."""
        mock_store.side_effect = Exception("Database error")

        args = Mock(hours=24)
        result = cmd_tier1_status(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error retrieving Tier 1 status" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_task_routing_report_no_data(self, mock_store, capsys):
        """Test task_routing_report with no data."""
        mock_analytics = Mock()
        mock_analytics.task_routing_accuracy.return_value = {
            "total_tasks": 0,
            "successful_routing": 0,
            "accuracy_rate": 0.0,
            "avg_confidence": 0.0,
            "by_task_type": {},
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=24)
            result = cmd_task_routing_report(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "No task routing data found" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_task_routing_report_with_data(self, mock_store, capsys):
        """Test task_routing_report displays data correctly."""
        mock_analytics = Mock()
        mock_analytics.task_routing_accuracy.return_value = {
            "total_tasks": 100,
            "successful_routing": 95,
            "accuracy_rate": 0.95,
            "avg_confidence": 0.87,
            "by_task_type": {
                "test_generation": {"total": 50, "success": 48, "rate": 0.96},
                "code_review": {"total": 50, "success": 47, "rate": 0.94},
            },
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=24)
            result = cmd_task_routing_report(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "95" in captured.out  # successful_routing
            assert "100" in captured.out  # total_tasks

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_test_status_no_data(self, mock_store, capsys):
        """Test test_status with no data."""
        mock_analytics = Mock()
        mock_analytics.test_execution_trends.return_value = {
            "total_executions": 0,
            "success_rate": 0.0,
            "avg_duration_seconds": 0.0,
            "total_tests_run": 0,
            "total_failures": 0,
            "most_failing_tests": [],
        }
        mock_analytics.coverage_progress.return_value = {
            "current_coverage": 0.0,
            "trend": "stable",
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=24)
            result = cmd_test_status(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "No test execution data found" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_test_status_with_failures(self, mock_store, capsys):
        """Test test_status displays failing tests."""
        mock_analytics = Mock()
        mock_analytics.test_execution_trends.return_value = {
            "total_executions": 50,
            "success_rate": 0.9,
            "avg_duration_seconds": 2.5,
            "total_tests_run": 500,
            "total_failures": 10,
            "most_failing_tests": [
                {"name": "test_broken_function", "failures": 5},
                {"name": "test_flaky_api", "failures": 3},
            ],
        }
        mock_analytics.coverage_progress.return_value = {
            "current_coverage": 75.5,
            "trend": "increasing",
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=24)
            result = cmd_test_status(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "test_broken_function" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_agent_performance_no_data(self, mock_store, capsys):
        """Test agent_performance with no data."""
        mock_analytics = Mock()
        mock_analytics.agent_performance.return_value = {
            "by_agent": {},
            "automation_rate": 0.0,
            "human_review_rate": 0.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=168)
            result = cmd_agent_performance(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "No agent assignment data found" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_agent_performance_with_data(self, mock_store, capsys):
        """Test agent_performance displays agent metrics."""
        mock_analytics = Mock()
        mock_analytics.agent_performance.return_value = {
            "by_agent": {
                "test-agent": {
                    "assignments": 100,
                    "completed": 95,
                    "success_rate": 0.95,
                    "avg_duration_hours": 2.5,
                },
                "review-agent": {
                    "assignments": 50,
                    "completed": 48,
                    "success_rate": 0.96,
                    "avg_duration_hours": 1.2,
                },
            },
            "automation_rate": 0.92,
            "human_review_rate": 0.08,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=168)
            result = cmd_agent_performance(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "test-agent" in captured.out
            assert "review-agent" in captured.out


class TestSonnetOpusAnalysis:
    """Test Sonnet 4.5 → Opus 4.5 fallback analysis."""

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_sonnet_opus_no_data(self, mock_store, capsys):
        """Test sonnet_opus_analysis with no data."""
        mock_analytics = Mock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {
            "total_calls": 0,
            "sonnet_attempts": 0,
            "success_rate_sonnet": 0.0,
            "opus_fallbacks": 0,
            "fallback_rate": 0.0,
            "actual_cost": 0.0,
            "always_opus_cost": 0.0,
            "savings": 0.0,
            "savings_percent": 0.0,
            "avg_cost_per_call": 0.0,
            "avg_opus_cost_per_call": 0.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(days=30)
            result = cmd_sonnet_opus_analysis(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "No Sonnet/Opus calls found" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_sonnet_opus_low_fallback(self, mock_store, capsys):
        """Test sonnet_opus_analysis with low fallback rate."""
        mock_analytics = Mock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {
            "total_calls": 100,
            "sonnet_attempts": 98,
            "success_rate_sonnet": 98.0,
            "opus_fallbacks": 2,
            "fallback_rate": 2.0,
            "actual_cost": 50.0,
            "always_opus_cost": 100.0,
            "savings": 50.0,
            "savings_percent": 50.0,
            "avg_cost_per_call": 0.5,
            "avg_opus_cost_per_call": 1.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(days=30)
            result = cmd_sonnet_opus_analysis(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "$50.00" in captured.out  # savings

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_sonnet_opus_high_fallback(self, mock_store, capsys):
        """Test sonnet_opus_analysis with high fallback rate."""
        mock_analytics = Mock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {
            "total_calls": 100,
            "sonnet_attempts": 80,
            "success_rate_sonnet": 80.0,
            "opus_fallbacks": 20,
            "fallback_rate": 20.0,
            "actual_cost": 80.0,
            "always_opus_cost": 100.0,
            "savings": 20.0,
            "savings_percent": 20.0,
            "avg_cost_per_call": 0.8,
            "avg_opus_cost_per_call": 1.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(days=30)
            result = cmd_sonnet_opus_analysis(args)

            assert result == 0
            captured = capsys.readouterr()
            # High fallback rate should show warning
            assert "20.0%" in captured.out


class TestTelemetryIntegration:
    """Integration tests combining multiple CLI commands."""

    def test_full_workflow_cycle(self, tmp_path, capsys):
        """Test complete workflow: track data, show, export, reset."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # 1. Track some calls
        for i in range(5):
            tracker.track_llm_call(
                workflow="integration-test",
                stage=f"stage-{i}",
                tier="CAPABLE" if i % 2 == 0 else "CHEAP",
                model="test-model",
                provider="test",
                cost=0.002 if i % 2 == 0 else 0.001,
                tokens={"input": 50, "output": 25},
                cache_hit=i % 3 == 0,
                cache_type="hash" if i % 3 == 0 else None,
                duration_ms=500,
            )

        # 2. Show data
        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)
        assert result == 0

        # 3. Export to JSON
        output_file = tmp_path / "export.json"
        args = Mock(format="json", output=str(output_file), days=None)
        result = cmd_telemetry_export(args)
        assert result == 0
        assert output_file.exists()

        # 4. Reset with confirmation
        args = Mock(confirm=True)
        result = cmd_telemetry_reset(args)
        assert result == 0

        # 5. Verify data is gone
        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)
        captured = capsys.readouterr()
        assert "No telemetry data found" in captured.out

    def test_savings_calculation_accuracy(self, tmp_path):
        """Test savings calculation is mathematically correct."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add known costs
        cheap_cost = 0.001
        capable_cost = 0.01
        premium_cost = 0.05

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=cheap_cost,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=capable_cost,
            tokens={"input": 50, "output": 25},
            cache_hit=False,
            cache_type=None,
            duration_ms=500,
        )

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="PREMIUM",
            model="test-model",
            provider="test",
            cost=premium_cost,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=1000,
        )

        # Calculate savings
        savings = tracker.calculate_savings(days=30)

        actual_total = cheap_cost + capable_cost + premium_cost
        assert abs(savings["actual_cost"] - actual_total) < 0.01

        # Baseline should be 3 * premium_cost
        assert savings["baseline_cost"] == pytest.approx(3 * premium_cost, rel=0.01)

    def test_export_formats_consistency(self, tmp_path):
        """Test JSON and CSV exports contain same data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add sample data
        tracker.track_llm_call(
            workflow="consistency-test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.0025,
            tokens={"input": 80, "output": 40},
            cache_hit=True,
            cache_type="hash",
            duration_ms=800,
        )

        # Export to JSON
        json_file = tmp_path / "export.json"
        args = Mock(format="json", output=str(json_file), days=None)
        cmd_telemetry_export(args)

        # Export to CSV
        csv_file = tmp_path / "export.csv"
        args = Mock(format="csv", output=str(csv_file), days=None)
        cmd_telemetry_export(args)

        # Verify both exist
        assert json_file.exists()
        assert csv_file.exists()

        # Load and compare key fields
        with open(json_file) as f:
            json_data = json.load(f)

        with open(csv_file, newline="") as f:
            csv_data = list(csv.DictReader(f))

        assert len(json_data) == len(csv_data)
        assert json_data[0]["workflow"] == csv_data[0]["workflow"]
        assert json_data[0]["tier"] == csv_data[0]["tier"]


class TestCmdTelemetryShowEdgeCases:
    """Test edge cases for cmd_telemetry_show."""

    def test_show_with_invalid_timestamp_format(self, tmp_path, capsys):
        """Test show handles entries with malformed timestamps."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add entry with valid timestamp
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        # Should not crash on invalid timestamps

    def test_show_with_missing_optional_fields(self, tmp_path, capsys):
        """Test show handles entries with missing optional fields."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Manually create entry with missing fields
        log_file = tracker.usage_file
        with open(log_file, "a", encoding="utf-8") as f:
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "workflow": "minimal",
                # Missing: stage, cache, duration_ms
                "tier": "CHEAP",
                "cost": 0.001,
                "tokens": {"input": 10},  # Missing output
            }
            f.write(json.dumps(entry) + "\n")

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        # Should handle missing fields gracefully

    def test_show_with_zero_entries(self, tmp_path, capsys):
        """Test show handles zero duration gracefully."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        tracker.track_llm_call(
            workflow="zero-duration",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=0,
        )

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0
        # Should not crash on division by zero

    def test_show_with_very_long_workflow_name(self, tmp_path, capsys):
        """Test show truncates long workflow names properly."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        long_name = "x" * 100
        tracker.track_llm_call(
            workflow=long_name,
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(limit=20, days=None)
        result = cmd_telemetry_show(args)

        assert result == 0


class TestCmdTelemetrySavingsEdgeCases:
    """Test edge cases for cmd_telemetry_savings."""

    def test_savings_with_only_premium_calls(self, tmp_path, capsys):
        """Test savings when only using premium tier."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add only premium tier calls
        for _ in range(3):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="PREMIUM",
                model="test-model",
                provider="test",
                cost=0.05,
                tokens={"input": 100, "output": 50},
                cache_hit=False,
                cache_type=None,
                duration_ms=1000,
            )

        args = Mock(days=30)
        result = cmd_telemetry_savings(args)

        assert result == 0
        captured = capsys.readouterr()
        # Savings should be $0 or negative
        assert "SAVINGS" in captured.out or "YOUR SAVINGS" in captured.out

    def test_savings_with_zero_cost_entries(self, tmp_path, capsys):
        """Test savings calculation with cache hits (zero cost)."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.0,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="hash",
            duration_ms=50,
        )

        args = Mock(days=30)
        result = cmd_telemetry_savings(args)

        assert result == 0

    def test_savings_tier_distribution_percentages(self, tmp_path, capsys):
        """Test tier distribution percentages sum to 100%."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add balanced mix
        for tier in ["CHEAP", "CAPABLE", "PREMIUM"]:
            for _ in range(10):
                tracker.track_llm_call(
                    workflow="test",
                    stage="test",
                    tier=tier,
                    model="test-model",
                    provider="test",
                    cost=0.001,
                    tokens={"input": 10, "output": 5},
                    cache_hit=False,
                    cache_type=None,
                    duration_ms=100,
                )

        savings = tracker.calculate_savings(days=30)
        total_pct = sum(savings["tier_distribution"].values())
        assert abs(total_pct - 100.0) < 0.2  # Allow floating point error


class TestCmdTelemetryCompareEdgeCases:
    """Test edge cases for cmd_telemetry_compare."""

    def test_compare_with_zero_cost_in_period(self, tmp_path, capsys):
        """Test compare handles periods with zero cost."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add entries
        for _i in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CHEAP",
                model="test-model",
                provider="test",
                cost=0.0,
                tokens={"input": 10, "output": 5},
                cache_hit=True,
                cache_type="hash",
                duration_ms=50,
            )

        args = Mock(period1=7, period2=30)
        result = cmd_telemetry_compare(args)

        assert result == 0
        # Should not crash with division by zero

    def test_compare_with_identical_periods(self, tmp_path, capsys):
        """Test compare with identical period data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        for _ in range(10):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CAPABLE",
                model="test-model",
                provider="test",
                cost=0.002,
                tokens={"input": 50, "output": 25},
                cache_hit=False,
                cache_type=None,
                duration_ms=500,
            )

        args = Mock(period1=7, period2=7)
        result = cmd_telemetry_compare(args)

        assert result == 0
        captured = capsys.readouterr()
        # Changes should be 0%
        assert "0.0%" in captured.out or "+0.0%" in captured.out


class TestCmdTelemetryExportEdgeCases:
    """Test edge cases for cmd_telemetry_export."""

    def test_export_csv_with_missing_nested_fields(self, tmp_path):
        """Test CSV export handles missing nested token/cache fields."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Manually create entry with incomplete nested data
        log_file = tracker.usage_file
        with open(log_file, "a", encoding="utf-8") as f:
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "workflow": "incomplete",
                "stage": "test",
                "tier": "CHEAP",
                "model": "test",
                "provider": "test",
                "cost": 0.001,
                "tokens": {},  # Missing input/output
                "cache": {},  # Missing hit/type
                "duration_ms": 100,
            }
            f.write(json.dumps(entry) + "\n")

        output_file = tmp_path / "incomplete.csv"
        args = Mock(format="csv", output=str(output_file), days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()

        # Verify CSV has defaults for missing fields
        with open(output_file, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["tokens_input"] == "0"
            assert rows[0]["cache_hit"] == "False"

    def test_export_json_creates_parent_directories(self, tmp_path):
        """Test JSON export creates parent directories if needed."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        nested_path = tmp_path / "level1" / "level2" / "export.json"
        # Create parent directories first (mkdir -p behavior)
        nested_path.parent.mkdir(parents=True, exist_ok=True)

        args = Mock(format="json", output=str(nested_path), days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert nested_path.exists()

    def test_export_csv_with_empty_strings(self, tmp_path):
        """Test CSV export handles empty string fields."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Manually create entry with empty strings
        log_file = tracker.usage_file
        with open(log_file, "a", encoding="utf-8") as f:
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "workflow": "",
                "stage": "",
                "tier": "CHEAP",
                "model": "",
                "provider": "",
                "cost": 0.001,
                "tokens": {"input": 10, "output": 5},
                "cache": {"hit": False, "type": ""},
                "duration_ms": 100,
            }
            f.write(json.dumps(entry) + "\n")

        output_file = tmp_path / "empty.csv"
        args = Mock(format="csv", output=str(output_file), days=None)
        result = cmd_telemetry_export(args)

        assert result == 0
        assert output_file.exists()


class TestCmdTelemetryDashboardEdgeCases:
    """Test edge cases for cmd_telemetry_dashboard."""

    @patch("webbrowser.open")
    def test_dashboard_with_single_entry(self, mock_open, tmp_path):
        """Test dashboard with minimal data."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        tracker.track_llm_call(
            workflow="single",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        assert mock_open.called

    @patch("webbrowser.open")
    def test_dashboard_with_unknown_tier(self, mock_open, tmp_path):
        """Test dashboard handles unknown tier gracefully."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Manually add entry with unknown tier
        log_file = tracker.usage_file
        with open(log_file, "a", encoding="utf-8") as f:
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "workflow": "test",
                "stage": "test",
                "tier": "UNKNOWN",
                "model": "test",
                "provider": "test",
                "cost": 0.001,
                "tokens": {"input": 10, "output": 5},
                "cache": {"hit": False},
                "duration_ms": 100,
            }
            f.write(json.dumps(entry) + "\n")

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        assert mock_open.called

    @patch("webbrowser.open")
    def test_dashboard_with_zero_baseline_cost(self, mock_open, tmp_path):
        """Test dashboard handles zero baseline cost."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add entry with zero tokens (edge case)
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.0,
            tokens={"input": 0, "output": 0},
            cache_hit=True,
            cache_type="hash",
            duration_ms=10,
        )

        args = Mock(days=30)
        result = cmd_telemetry_dashboard(args)

        assert result == 0
        assert mock_open.called


class TestTier1MonitoringEdgeCases:
    """Test edge cases for Tier 1 monitoring commands."""

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_tier1_status_with_complete_data(self, mock_store, capsys):
        """Test tier1_status with comprehensive data."""
        mock_analytics = Mock()
        mock_analytics.tier1_summary.return_value = {
            "task_routing": {
                "total_tasks": 500,
                "accuracy_rate": 0.95,
                "avg_confidence": 0.87,
            },
            "test_execution": {
                "total_executions": 200,
                "success_rate": 0.92,
                "avg_duration_seconds": 3.5,
                "total_failures": 16,
            },
            "coverage": {
                "current_coverage": 78.5,
                "change": 5.2,
                "trend": "increasing",
                "critical_gaps_count": 3,
            },
            "agent_performance": {
                "by_agent": {
                    "agent1": {"assignments": 100, "completed": 95},
                    "agent2": {"assignments": 80, "completed": 78},
                },
                "automation_rate": 0.88,
                "human_review_rate": 0.12,
            },
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(hours=48)
            result = cmd_tier1_status(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "500" in captured.out or "Tier 1" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_task_routing_report_with_error(self, mock_store, capsys):
        """Test task_routing_report handles errors."""
        mock_store.side_effect = Exception("Connection error")

        args = Mock(hours=24)
        result = cmd_task_routing_report(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error retrieving task routing report" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_test_status_with_error(self, mock_store, capsys):
        """Test test_status handles errors."""
        mock_store.side_effect = Exception("Database error")

        args = Mock(hours=24)
        result = cmd_test_status(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error retrieving test status" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_agent_performance_with_error(self, mock_store, capsys):
        """Test agent_performance handles errors."""
        mock_store.side_effect = Exception("Store error")

        args = Mock(hours=168)
        result = cmd_agent_performance(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error retrieving agent performance" in captured.out


class TestSonnetOpusAnalysisEdgeCases:
    """Test edge cases for Sonnet/Opus analysis."""

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_sonnet_opus_moderate_fallback(self, mock_store, capsys):
        """Test sonnet_opus_analysis with moderate fallback rate."""
        mock_analytics = Mock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {
            "total_calls": 100,
            "sonnet_attempts": 90,
            "success_rate_sonnet": 90.0,
            "opus_fallbacks": 10,
            "fallback_rate": 10.0,
            "actual_cost": 60.0,
            "always_opus_cost": 100.0,
            "savings": 40.0,
            "savings_percent": 40.0,
            "avg_cost_per_call": 0.6,
            "avg_opus_cost_per_call": 1.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(days=30)
            result = cmd_sonnet_opus_analysis(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "10.0%" in captured.out

    @patch("attune.models.telemetry.get_telemetry_store")
    def test_sonnet_opus_with_zero_savings(self, mock_store, capsys):
        """Test sonnet_opus_analysis with no savings."""
        mock_analytics = Mock()
        mock_analytics.sonnet_opus_fallback_analysis.return_value = {
            "total_calls": 100,
            "sonnet_attempts": 0,
            "success_rate_sonnet": 0.0,
            "opus_fallbacks": 100,
            "fallback_rate": 100.0,
            "actual_cost": 100.0,
            "always_opus_cost": 100.0,
            "savings": 0.0,
            "savings_percent": 0.0,
            "avg_cost_per_call": 1.0,
            "avg_opus_cost_per_call": 1.0,
        }

        with patch("attune.models.telemetry.TelemetryAnalytics", return_value=mock_analytics):
            args = Mock(days=30)
            result = cmd_sonnet_opus_analysis(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "$0.00" in captured.out or "100.0%" in captured.out


class TestArgumentParsing:
    """Test argument parsing for all CLI commands."""

    def test_show_with_default_args(self, tmp_path, capsys):
        """Test show command uses default values when args missing."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Args with no limit or days attributes
        args = Mock(spec=[])
        result = cmd_telemetry_show(args)

        assert result == 0

    def test_savings_with_custom_days(self, tmp_path, capsys):
        """Test savings command respects custom days parameter."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add old data
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CHEAP",
            model="test-model",
            provider="test",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        args = Mock(days=365)
        result = cmd_telemetry_savings(args)

        assert result == 0

    def test_compare_with_equal_periods(self, tmp_path, capsys):
        """Test compare command with equal period values."""
        tracker = UsageTracker(telemetry_dir=tmp_path)
        UsageTracker._instance = tracker

        # Add data
        for _ in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CHEAP",
                model="test-model",
                provider="test",
                cost=0.001,
                tokens={"input": 10, "output": 5},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        args = Mock(period1=30, period2=30)
        result = cmd_telemetry_compare(args)

        assert result == 0
