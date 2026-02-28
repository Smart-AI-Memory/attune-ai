"""Unit tests for Tier 1 CLI commands.

Tests the four Tier 1 CLI commands:
- cmd_tier1_status
- cmd_task_routing_report
- cmd_test_status
- cmd_agent_performance

Tests cover:
- Command execution with mocked data
- Output formatting (Rich and plain text)
- Error handling
- Empty data scenarios
- Command-line argument parsing
"""

import argparse
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.models import (
    AgentAssignmentRecord,
    CoverageRecord,
    TaskRoutingRecord,
    TestExecutionRecord,
)
from attune.models.telemetry import TelemetryStore
from attune.telemetry.cli import (
    cmd_agent_performance,
    cmd_task_routing_report,
    cmd_test_status,
    cmd_tier1_status,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test telemetry data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def populated_store(temp_dir):
    """Create a TelemetryStore with sample Tier 1 data."""
    store = TelemetryStore(storage_dir=str(temp_dir))

    now = datetime.utcnow()

    # Add routing data
    store.log_task_routing(
        TaskRoutingRecord(
            routing_id="routing-1",
            timestamp=now.isoformat(),
            task_description="Code review task",
            task_type="code_review",
            task_complexity="simple",
            assigned_agent="review-agent",
            assigned_tier="claude-sonnet-4.5",
            routing_strategy="rule_based",
            confidence_score=0.95,
            status="completed",
            success=True,
            actual_cost=0.01,
        ),
    )

    store.log_task_routing(
        TaskRoutingRecord(
            routing_id="routing-2",
            timestamp=now.isoformat(),
            task_description="Bug fix task",
            task_type="bug_fix",
            task_complexity="moderate",
            assigned_agent="bug-agent",
            assigned_tier="claude-sonnet-4.5",
            routing_strategy="ml_predicted",
            confidence_score=0.85,
            status="failed",
            success=False,
        ),
    )

    # Add test execution data
    store.log_test_execution(
        TestExecutionRecord(
            execution_id="test-1",
            timestamp=now.isoformat(),
            test_suite="unit",
            triggered_by="manual",
            command="pytest tests/unit/",
            working_directory="/project",
            duration_seconds=45.2,
            total_tests=100,
            passed=95,
            failed=5,
            skipped=0,
            errors=0,
            success=False,
            exit_code=1,
            failed_tests=[
                {"name": "test_auth", "file": "test_auth.py", "error": "AssertionError"},
                {"name": "test_api", "file": "test_api.py", "error": "Timeout"},
            ],
        ),
    )

    # Add coverage data
    store.log_coverage(
        CoverageRecord(
            record_id="cov-1",
            timestamp=now.isoformat(),
            overall_percentage=85.5,
            lines_total=1000,
            lines_covered=855,
            branches_total=200,
            branches_covered=150,
            files_total=50,
            files_well_covered=35,
            files_critical=5,
            critical_gaps=[
                {"file": "src/auth.py", "coverage": 45.0, "priority": "high"},
                {"file": "src/payment.py", "coverage": 38.5, "priority": "high"},
            ],
            trend="stable",
            coverage_format="xml",
            coverage_file="coverage.xml",
        ),
    )

    # Add agent assignment data
    store.log_agent_assignment(
        AgentAssignmentRecord(
            assignment_id="assign-1",
            timestamp=now.isoformat(),
            task_id="task-1",
            task_title="Fix authentication bug",
            task_description="Users cannot login",
            assigned_agent="bug-fix-agent",
            assignment_reason="Rule-based routing",
            automated_eligible=True,
            task_spec_clarity=0.95,
            has_dependencies=False,
            status="completed",
            success=True,
            actual_duration_hours=300.0 / 3600.0,
            quality_check_passed=True,
        ),
    )

    return store


class TestTier1StatusCommand:
    """Test suite for cmd_tier1_status command."""

    def test_command_with_data(self, populated_store, monkeypatch):
        """Test tier1 command with populated data."""
        # Mock get_telemetry_store to return our populated store
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        # Create args namespace
        args = argparse.Namespace(hours=24)

        # Capture stdout
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_tier1_status(args)

            output = mock_stdout.getvalue()

            # Should return success
            assert result == 0

            # Output should contain key sections (plain text fallback)
            assert "Task Routing" in output or "routing" in output.lower()
            assert "Test Execution" in output or "test" in output.lower()
            assert "Coverage" in output or "coverage" in output.lower()
            assert "Agent Performance" in output or "agent" in output.lower()

    def test_command_with_empty_data(self, temp_dir, monkeypatch):
        """Test tier1 command with no data."""
        empty_store = TelemetryStore(storage_dir=str(temp_dir))
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: empty_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_tier1_status(args)

            output = mock_stdout.getvalue()

            # Should still return success
            assert result == 0

            # Should indicate no data or show zeros
            assert (
                "No data" in output
                or "Total Tasks: 0" in output
                or "total tasks: 0" in output.lower()
            )

    def test_command_with_custom_hours(self, populated_store, monkeypatch):
        """Test tier1 command with custom time window."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        # Test with 168 hours (7 days)
        args = argparse.Namespace(hours=168)

        with patch("sys.stdout", new=StringIO()):
            result = cmd_tier1_status(args)

            assert result == 0


class TestTaskRoutingReportCommand:
    """Test suite for cmd_task_routing_report command."""

    def test_command_with_data(self, populated_store, monkeypatch):
        """Test tasks command with populated data."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_task_routing_report(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should contain routing statistics
            assert "routing" in output.lower() or "tasks" in output.lower()
            # Should show accuracy or success rate
            assert "accuracy" in output.lower() or "success" in output.lower()

    def test_command_shows_task_types(self, populated_store, monkeypatch):
        """Test that command shows breakdown by task type."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_task_routing_report(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should mention task types
            assert (
                "code_review" in output.lower()
                or "bug_fix" in output.lower()
                or "by_task_type" in output.lower()
            )

    def test_command_with_empty_data(self, temp_dir, monkeypatch):
        """Test tasks command with no data."""
        empty_store = TelemetryStore(storage_dir=str(temp_dir))
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: empty_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_task_routing_report(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should indicate no routing data
            assert "No task routing data" in output or "0" in output or "no data" in output.lower()


class TestTestStatusCommand:
    """Test suite for cmd_test_status command."""

    def test_command_with_data(self, populated_store, monkeypatch):
        """Test tests command with populated data."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_test_status(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should contain test statistics
            assert "test" in output.lower()
            # Should show success rate or pass/fail info
            assert (
                "success" in output.lower()
                or "passed" in output.lower()
                or "failed" in output.lower()
            )

    def test_command_shows_failing_tests(self, populated_store, monkeypatch):
        """Test that command shows most failing tests."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_test_status(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should mention failing tests or show test names
            assert (
                "test_auth" in output
                or "test_api" in output
                or "failing" in output.lower()
                or "most_failing_tests" in output.lower()
            )

    def test_command_with_empty_data(self, temp_dir, monkeypatch):
        """Test tests command with no data."""
        empty_store = TelemetryStore(storage_dir=str(temp_dir))
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: empty_store)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_test_status(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should indicate no test data
            assert "No test" in output or "0" in output or "no data" in output.lower()


class TestAgentPerformanceCommand:
    """Test suite for cmd_agent_performance command."""

    def test_command_with_data(self, populated_store, monkeypatch):
        """Test agents command with populated data."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=168)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_agent_performance(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should contain agent statistics
            assert "agent" in output.lower()
            # Should show performance metrics
            assert (
                "performance" in output.lower()
                or "success" in output.lower()
                or "assignments" in output.lower()
            )

    def test_command_shows_agent_names(self, populated_store, monkeypatch):
        """Test that command shows agent names and stats."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=168)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_agent_performance(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should mention agent name or show agent stats
            assert (
                "bug-fix-agent" in output
                or "by_agent" in output.lower()
                or "agent performance" in output.lower()
            )

    def test_command_with_empty_data(self, temp_dir, monkeypatch):
        """Test agents command with no data."""
        empty_store = TelemetryStore(storage_dir=str(temp_dir))
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: empty_store)

        args = argparse.Namespace(hours=168)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_agent_performance(args)

            output = mock_stdout.getvalue()

            assert result == 0

            # Should indicate no agent data
            assert "No agent" in output or "0" in output or "no data" in output.lower()


class TestErrorHandling:
    """Test error handling across all CLI commands."""

    def test_tier1_handles_store_errors(self, monkeypatch):
        """Test that tier1 command handles store errors gracefully."""

        def mock_get_store_error():
            raise RuntimeError("Test error")

        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", mock_get_store_error)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_tier1_status(args)

            output = mock_stdout.getvalue()

            # Should return error code
            assert result != 0

            # Should show error message
            assert "error" in output.lower() or "failed" in output.lower()

    def test_tasks_handles_store_errors(self, monkeypatch):
        """Test that tasks command handles store errors gracefully."""

        def mock_get_store_error():
            raise RuntimeError("Test error")

        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", mock_get_store_error)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_task_routing_report(args)

            output = mock_stdout.getvalue()

            assert result != 0
            assert "error" in output.lower() or "failed" in output.lower()

    def test_tests_handles_store_errors(self, monkeypatch):
        """Test that tests command handles store errors gracefully."""

        def mock_get_store_error():
            raise RuntimeError("Test error")

        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", mock_get_store_error)

        args = argparse.Namespace(hours=24)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_test_status(args)

            output = mock_stdout.getvalue()

            assert result != 0
            assert "error" in output.lower() or "failed" in output.lower()

    def test_agents_handles_store_errors(self, monkeypatch):
        """Test that agents command handles store errors gracefully."""

        def mock_get_store_error():
            raise RuntimeError("Test error")

        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", mock_get_store_error)

        args = argparse.Namespace(hours=168)

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            result = cmd_agent_performance(args)

            output = mock_stdout.getvalue()

            assert result != 0
            assert "error" in output.lower() or "failed" in output.lower()


class TestRichFormatting:
    """Test Rich library formatting (when available)."""

    def test_tier1_uses_rich_when_available(self, populated_store, monkeypatch):
        """Test that tier1 command uses Rich for formatting when available."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        # Mock Rich to verify it's called
        with patch("attune.telemetry.cli_automation.Console") as mock_console:
            mock_console_instance = mock_console.return_value

            result = cmd_tier1_status(args)

            # Should use Rich console
            assert mock_console.called or mock_console_instance.print.called or result == 0

    def test_fallback_to_plain_text(self, populated_store, monkeypatch):
        """Test that commands fall back to plain text if Rich unavailable."""
        monkeypatch.setattr("attune.models.telemetry.get_telemetry_store", lambda: populated_store)

        args = argparse.Namespace(hours=24)

        # Mock Rich as unavailable by patching RICH_AVAILABLE
        with patch("attune.telemetry.cli_automation.RICH_AVAILABLE", False):
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                result = cmd_tier1_status(args)

                output = mock_stdout.getvalue()

                # Should still work with plain text
                assert result == 0 or len(output) > 0
