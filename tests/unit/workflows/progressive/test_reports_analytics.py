"""Tests for reporting, analytics, and result storage in progressive workflows."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from attune.workflows.progressive.core import (
    FailureAnalysis,
    ProgressiveWorkflowResult,
    Tier,
    TierResult,
)
from attune.workflows.progressive.reports import (
    _format_duration,
    cleanup_old_results,
    format_cost_analytics_report,
    generate_cost_analytics,
    generate_progression_report,
    list_saved_results,
    load_result_from_disk,
    save_results_to_disk,
)


class TestReportGeneration:
    """Test report generation."""

    def test_format_duration_seconds(self):
        """Test formatting duration under 60 seconds."""
        assert _format_duration(12.3) == "12s"
        assert _format_duration(45.9) == "45s"

    def test_format_duration_minutes(self):
        """Test formatting duration with minutes."""
        assert _format_duration(83.5) == "1m 23s"  # int(83.5) = 83, 83 % 60 = 23
        assert _format_duration(125.0) == "2m 5s"

    def test_generate_progression_report_single_tier(self):
        """Test generating report for single-tier execution."""
        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=90.0,
                assertion_depth=3.0,
                confidence_score=0.95,
            ),
            cost=0.30,
            duration=10.5,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=0.30,
            total_duration=10.5,
            success=True,
        )

        report = generate_progression_report(result)

        assert "PROGRESSIVE ESCALATION REPORT" in report
        assert "test-gen" in report
        assert "CHEAP Tier" in report
        assert "$0.30" in report
        assert "✅" in report  # Success icon

    def test_generate_progression_report_multi_tier(self):
        """Test generating report for multi-tier execution with escalation."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 60}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=75.0,
                coverage_percent=65.0,
                assertion_depth=2.0,
                confidence_score=0.80,
            ),
            cost=0.30,
            duration=10.0,
            escalated=True,
            escalation_reason="Low CQS (60)",
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 95}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=95.0,
                assertion_depth=4.0,
                confidence_score=0.98,
            ),
            cost=0.45,
            duration=15.0,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-120000",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.75,
            total_duration=25.0,
            success=True,
        )

        report = generate_progression_report(result)

        assert "CHEAP Tier" in report
        assert "CAPABLE Tier" in report
        assert "Low CQS (60)" in report  # Escalation reason
        assert "$0.75" in report  # Total cost


class TestResultStorage:
    """Test result storage and loading."""

    def test_save_and_load_result(self, tmp_path):
        """Test saving and loading results from disk."""
        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            failure_analysis=FailureAnalysis(
                syntax_errors=[],
                test_pass_rate=100.0,
                coverage_percent=90.0,
                assertion_depth=3.0,
                confidence_score=0.95,
            ),
            cost=0.30,
            duration=10.0,
        )

        result = ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-task-001",
            tier_results=[tier_result],
            final_result=tier_result,
            total_cost=0.30,
            total_duration=10.0,
            success=True,
        )

        # Save to disk
        storage_path = str(tmp_path / "progressive_runs")
        save_results_to_disk(result, storage_path)

        # Verify files created
        task_dir = Path(storage_path) / "test-task-001"
        assert task_dir.exists()
        assert (task_dir / "summary.json").exists()
        assert (task_dir / "tier_0_cheap.json").exists()
        assert (task_dir / "report.txt").exists()

        # Load back from disk
        loaded = load_result_from_disk("test-task-001", storage_path)

        assert loaded["summary"]["workflow"] == "test-gen"
        assert loaded["summary"]["total_cost"] == 0.30
        assert len(loaded["tier_results"]) == 1
        assert loaded["report"] != ""

    def test_load_nonexistent_task(self, tmp_path):
        """Test loading nonexistent task raises FileNotFoundError."""
        storage_path = str(tmp_path / "progressive_runs")

        with pytest.raises(FileNotFoundError, match="not found"):
            load_result_from_disk("nonexistent-task", storage_path)

    def test_list_saved_results_empty(self, tmp_path):
        """Test listing results when storage is empty."""
        storage_path = str(tmp_path / "progressive_runs")
        results = list_saved_results(storage_path)

        assert results == []

    def test_list_saved_results_multiple(self, tmp_path):
        """Test listing multiple saved results."""
        # Create mock results
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        for i in range(3):
            task_dir = storage_path / f"test-task-00{i}"
            task_dir.mkdir()

            summary = {
                "workflow": "test-gen",
                "task_id": f"test-task-00{i}",
                "timestamp": (datetime.now() - timedelta(days=i)).isoformat(),
                "total_cost": 0.30 + (i * 0.1),
                "success": True,
            }

            (task_dir / "summary.json").write_text(json.dumps(summary))

        # List results
        results = list_saved_results(str(storage_path))

        assert len(results) == 3
        # Should be sorted by timestamp (newest first)
        assert results[0]["task_id"] == "test-task-000"
        assert results[2]["task_id"] == "test-task-002"


class TestCleanupPolicy:
    """Test retention policy and cleanup."""

    def test_cleanup_old_results_dry_run(self, tmp_path):
        """Test cleanup in dry-run mode."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        # Create old result (40 days ago)
        old_task_dir = storage_path / "old-task"
        old_task_dir.mkdir()
        old_summary = {
            "task_id": "old-task",
            "timestamp": (datetime.now() - timedelta(days=40)).isoformat(),
        }
        (old_task_dir / "summary.json").write_text(json.dumps(old_summary))

        # Create recent result (10 days ago)
        recent_task_dir = storage_path / "recent-task"
        recent_task_dir.mkdir()
        recent_summary = {
            "task_id": "recent-task",
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
        }
        (recent_task_dir / "summary.json").write_text(json.dumps(recent_summary))

        # Dry run cleanup (30 day retention)
        deleted, retained = cleanup_old_results(
            storage_path=str(storage_path),
            retention_days=30,
            dry_run=True,
        )

        assert deleted == 1  # Would delete old-task
        assert retained == 1  # Would retain recent-task
        # Verify nothing actually deleted
        assert old_task_dir.exists()
        assert recent_task_dir.exists()

    def test_cleanup_old_results_actual(self, tmp_path):
        """Test actual cleanup (not dry-run)."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        # Create old result
        old_task_dir = storage_path / "old-task"
        old_task_dir.mkdir()
        old_summary = {
            "task_id": "old-task",
            "timestamp": (datetime.now() - timedelta(days=40)).isoformat(),
        }
        (old_task_dir / "summary.json").write_text(json.dumps(old_summary))

        # Cleanup (30 day retention)
        deleted, retained = cleanup_old_results(
            storage_path=str(storage_path),
            retention_days=30,
            dry_run=False,
        )

        assert deleted == 1
        assert retained == 0
        # Verify actually deleted
        assert not old_task_dir.exists()

    def test_cleanup_empty_storage(self, tmp_path):
        """Test cleanup on empty storage path."""
        storage_path = str(tmp_path / "progressive_runs")

        deleted, retained = cleanup_old_results(storage_path=storage_path)

        assert deleted == 0
        assert retained == 0


class TestCostAnalytics:
    """Test cost analytics generation."""

    def test_generate_analytics_no_results(self, tmp_path):
        """Test analytics generation with no results."""
        storage_path = str(tmp_path / "progressive_runs")
        analytics = generate_cost_analytics(storage_path)

        assert analytics["total_runs"] == 0
        assert analytics["total_cost"] == 0.0
        assert analytics["total_savings"] == 0.0

    def test_generate_analytics_single_result(self, tmp_path):
        """Test analytics generation with single result."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        task_dir = storage_path / "test-task-001"
        task_dir.mkdir()

        summary = {
            "workflow": "test-gen",
            "task_id": "test-task-001",
            "timestamp": datetime.now().isoformat(),
            "total_cost": 0.75,
            "cost_savings": 4.25,
            "cost_savings_percent": 85.0,
            "success": True,
            "tier_count": 2,
            "final_cqs": 92.0,
        }
        (task_dir / "summary.json").write_text(json.dumps(summary))

        analytics = generate_cost_analytics(str(storage_path))

        assert analytics["total_runs"] == 1
        assert analytics["total_cost"] == 0.75
        assert analytics["total_savings"] == 4.25
        assert analytics["escalation_rate"] == 1.0  # 1 result with 2 tiers = escalation
        assert analytics["success_rate"] == 1.0

    def test_generate_analytics_multiple_results(self, tmp_path):
        """Test analytics generation with multiple results."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        # Create 3 results
        for i in range(3):
            task_dir = storage_path / f"test-task-00{i}"
            task_dir.mkdir()

            summary = {
                "workflow": "test-gen" if i < 2 else "code-review",
                "task_id": f"test-task-00{i}",
                "timestamp": datetime.now().isoformat(),
                "total_cost": 0.50 + (i * 0.2),
                "cost_savings": 2.0 + (i * 0.5),
                "cost_savings_percent": 80.0 - (i * 5),
                "success": i < 2,  # First 2 succeed, last fails
                "tier_count": 1 + i,  # Varying tier counts
                "final_cqs": 85.0 + (i * 3),
            }
            (task_dir / "summary.json").write_text(json.dumps(summary))

        analytics = generate_cost_analytics(str(storage_path))

        assert analytics["total_runs"] == 3
        # Costs: 0.50 + 0.70 + 0.90 = 2.10
        assert analytics["total_cost"] == pytest.approx(2.10, rel=0.01)
        # Savings: 2.0 + 2.5 + 3.0 = 7.5
        assert analytics["total_savings"] == pytest.approx(7.5, rel=0.01)
        assert analytics["escalation_rate"] == pytest.approx(0.67, rel=0.01)  # 2 out of 3
        assert analytics["success_rate"] == pytest.approx(0.67, rel=0.01)  # 2 out of 3

        # Check per-workflow stats
        assert "test-gen" in analytics["workflow_stats"]
        assert "code-review" in analytics["workflow_stats"]

        test_gen_stats = analytics["workflow_stats"]["test-gen"]
        assert test_gen_stats["runs"] == 2
        assert test_gen_stats["successes"] == 2

    def test_format_analytics_report(self, tmp_path):
        """Test formatting analytics as report."""
        analytics = {
            "total_runs": 10,
            "total_cost": 8.50,
            "total_savings": 41.50,
            "avg_savings_percent": 83.0,
            "escalation_rate": 0.60,
            "success_rate": 0.90,
            "avg_final_cqs": 88.5,
            "tier_usage": {},
            "tier_costs": {},
            "workflow_stats": {
                "test-gen": {
                    "runs": 7,
                    "avg_cost": 0.85,
                    "avg_savings": 4.15,
                    "success_rate": 0.86,
                },
                "code-review": {
                    "runs": 3,
                    "avg_cost": 0.83,
                    "avg_savings": 4.17,
                    "success_rate": 1.0,
                },
            },
        }

        report = format_cost_analytics_report(analytics)

        assert "PROGRESSIVE ESCALATION ANALYTICS" in report
        assert "Total Runs: 10" in report
        assert "$8.50" in report
        assert "83.0%" in report
        assert "test-gen:" in report
        assert "code-review:" in report


class TestCLI:
    """Test CLI commands."""

    def test_cli_list_results_empty(self, tmp_path, capsys):
        """Test CLI list command with no results."""
        from attune.workflows.progressive.cli import cmd_list_results

        args = MagicMock()
        args.storage_path = str(tmp_path / "progressive_runs")

        exit_code = cmd_list_results(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_cli_show_report_nonexistent(self, tmp_path, capsys):
        """Test CLI show command with nonexistent task."""
        from attune.workflows.progressive.cli import cmd_show_report

        args = MagicMock()
        args.task_id = "nonexistent"
        args.storage_path = str(tmp_path / "progressive_runs")
        args.json = False

        exit_code = cmd_show_report(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_cli_analytics_no_results(self, tmp_path, capsys):
        """Test CLI analytics command with no results."""
        from attune.workflows.progressive.cli import cmd_analytics

        args = MagicMock()
        args.storage_path = str(tmp_path / "progressive_runs")
        args.json = False

        exit_code = cmd_analytics(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_cli_cleanup_dry_run(self, tmp_path, capsys):
        """Test CLI cleanup command in dry-run mode."""
        from attune.workflows.progressive.cli import cmd_cleanup

        # Create old result
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir(parents=True)

        task_dir = storage_path / "old-task"
        task_dir.mkdir()
        summary = {
            "task_id": "old-task",
            "timestamp": (datetime.now() - timedelta(days=40)).isoformat(),
        }
        (task_dir / "summary.json").write_text(json.dumps(summary))

        args = MagicMock()
        args.storage_path = str(storage_path)
        args.retention_days = 30
        args.dry_run = True

        exit_code = cmd_cleanup(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Dry run mode" in captured.out
        assert "Would delete: 1" in captured.out
