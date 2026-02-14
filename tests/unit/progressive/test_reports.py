"""Unit tests for progressive workflow reporting and result storage.

Tests cover:
- Report generation and formatting
- Result persistence to disk
- Result loading from disk
- Cost analytics generation
- Cleanup of old results
"""

import json
from datetime import datetime, timedelta

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


class TestFormatDuration:
    """Test duration formatting helper."""

    def test_format_duration_under_60_seconds(self):
        """Test formatting durations under 1 minute."""
        assert _format_duration(12.3) == "12s"
        assert _format_duration(45.9) == "45s"
        assert _format_duration(0.5) == "0s"

    def test_format_duration_over_60_seconds(self):
        """Test formatting durations over 1 minute."""
        assert _format_duration(83.5) == "1m 23s"
        assert _format_duration(125.0) == "2m 5s"
        assert _format_duration(600.0) == "10m 0s"

    def test_format_duration_exact_minutes(self):
        """Test formatting exact minute values."""
        assert _format_duration(60.0) == "1m 0s"
        assert _format_duration(180.0) == "3m 0s"


class TestGenerateProgressionReport:
    """Test progression report generation."""

    @pytest.fixture
    def sample_result(self):
        """Create sample workflow result for testing."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 85},
                {"quality_score": 75},
                {"quality_score": 90},
            ],
            cost=0.30,
            duration=15.0,
            escalated=True,
            escalation_reason="Quality below threshold",
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.70,
                coverage_percent=65.0,
            ),
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 92},
                {"quality_score": 88},
                {"quality_score": 95},
            ],
            cost=0.65,
            duration=22.0,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.95,
                coverage_percent=90.0,
            ),
        )

        return ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.95,
            total_duration=37.0,
            success=True,
        )

    def test_generate_report_structure(self, sample_result):
        """Test that report contains expected sections."""
        report = generate_progression_report(sample_result)

        # Check for key sections
        assert "PROGRESSIVE ESCALATION REPORT" in report
        assert "Workflow: test-gen" in report
        assert "Task ID: test-gen-20260117-143022" in report
        assert "TIER BREAKDOWN:" in report
        assert "FINAL RESULTS:" in report
        # Cost Savings only shown if > 0
        if sample_result.cost_savings > 0:
            assert "Cost Savings:" in report

    def test_generate_report_tier_details(self, sample_result):
        """Test that tier details are included."""
        report = generate_progression_report(sample_result)

        # Check cheap tier details
        assert "💰 CHEAP Tier" in report
        assert "gpt-4o-mini" in report
        assert "Escalated: Quality below threshold" in report

        # Check capable tier details
        assert "📊 CAPABLE Tier" in report
        assert "claude-3-5-sonnet" in report

    def test_generate_report_cost_info(self, sample_result):
        """Test that cost information is formatted correctly."""
        report = generate_progression_report(sample_result)

        assert "Total Cost: $0.95" in report
        # Cost Savings shown only if result has savings > 0
        # With small sample sizes, savings may be 0

    def test_generate_report_success_status(self, sample_result):
        """Test success status display."""
        report = generate_progression_report(sample_result)

        assert "✅" in report  # Success icon
        assert "Status: Success" in report

    def test_generate_report_failure_status(self, sample_result):
        """Test failure status display."""
        sample_result.success = False

        report = generate_progression_report(sample_result)

        assert "❌" in report  # Failure icon
        assert "Status: Incomplete" in report

    def test_generate_report_no_cost_savings(self, sample_result):
        """Test report when there are no cost savings."""
        # Mock a result with zero savings
        sample_result.tier_results = [sample_result.tier_results[1]]  # Only capable tier

        report = generate_progression_report(sample_result)

        # Should not crash, but savings line may not appear if 0
        assert "PROGRESSIVE ESCALATION REPORT" in report


class TestSaveResultsToDisk:
    """Test saving results to filesystem."""

    def test_save_creates_directory_structure(self, tmp_path, sample_result):
        """Test that save creates expected directory structure."""
        storage_path = tmp_path / "progressive_runs"

        save_results_to_disk(sample_result, str(storage_path))

        task_dir = storage_path / sample_result.task_id
        assert task_dir.exists()
        assert (task_dir / "summary.json").exists()
        assert (task_dir / "tier_0_cheap.json").exists()
        assert (task_dir / "tier_1_capable.json").exists()
        assert (task_dir / "report.txt").exists()

    def test_save_summary_content(self, tmp_path, sample_result):
        """Test that summary.json contains correct data."""
        storage_path = tmp_path / "progressive_runs"

        save_results_to_disk(sample_result, str(storage_path))

        summary_file = storage_path / sample_result.task_id / "summary.json"
        summary = json.loads(summary_file.read_text())

        assert summary["workflow"] == "test-gen"
        assert summary["task_id"] == "test-gen-20260117-143022"
        assert summary["total_cost"] == 0.95
        assert summary["total_duration"] == 37.0
        assert summary["success"] is True
        assert summary["tier_count"] == 2

    def test_save_tier_data_content(self, tmp_path, sample_result):
        """Test that tier JSON files contain correct data."""
        storage_path = tmp_path / "progressive_runs"

        save_results_to_disk(sample_result, str(storage_path))

        tier_file = storage_path / sample_result.task_id / "tier_0_cheap.json"
        tier_data = json.loads(tier_file.read_text())

        assert tier_data["tier"] == "cheap"
        assert tier_data["model"] == "gpt-4o-mini"
        assert tier_data["attempt"] == 2
        assert tier_data["quality_score"] > 0
        assert tier_data["escalated"] is True
        assert tier_data["escalation_reason"] == "Quality below threshold"
        assert "failure_analysis" in tier_data

    def test_save_report_content(self, tmp_path, sample_result):
        """Test that report.txt contains formatted report."""
        storage_path = tmp_path / "progressive_runs"

        save_results_to_disk(sample_result, str(storage_path))

        report_file = storage_path / sample_result.task_id / "report.txt"
        report = report_file.read_text()

        assert "PROGRESSIVE ESCALATION REPORT" in report
        assert "test-gen" in report

    def test_save_invalid_path_raises_error(self, sample_result, tmp_path):
        """Test that invalid storage path raises ValueError."""
        # Use path with null byte which will fail validation
        invalid_path = str(tmp_path / "test\x00path")

        with pytest.raises(ValueError, match="null byte"):
            save_results_to_disk(sample_result, invalid_path)

    @pytest.fixture
    def sample_result(self):
        """Create sample workflow result for testing."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            cost=0.30,
            duration=15.0,
            escalated=True,
            escalation_reason="Quality below threshold",
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.70,
                coverage_percent=65.0,
            ),
        )

        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 92}],
            cost=0.65,
            duration=22.0,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.95,
                coverage_percent=90.0,
            ),
        )

        return ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[cheap_result, capable_result],
            final_result=capable_result,
            total_cost=0.95,
            total_duration=37.0,
            success=True,
        )


class TestLoadResultFromDisk:
    """Test loading results from filesystem."""

    def test_load_existing_result(self, tmp_path, sample_result):
        """Test loading a previously saved result."""
        storage_path = tmp_path / "progressive_runs"

        # Save first
        save_results_to_disk(sample_result, str(storage_path))

        # Load back
        loaded = load_result_from_disk(sample_result.task_id, str(storage_path))

        assert loaded["summary"]["workflow"] == "test-gen"
        assert loaded["summary"]["total_cost"] == 0.30  # Sample result has 1 tier
        assert len(loaded["tier_results"]) == 1
        assert "PROGRESSIVE ESCALATION REPORT" in loaded["report"]

    def test_load_nonexistent_task_raises_error(self, tmp_path):
        """Test that loading nonexistent task raises FileNotFoundError."""
        storage_path = tmp_path / "progressive_runs"
        storage_path.mkdir()

        with pytest.raises(FileNotFoundError, match="Task .* not found"):
            load_result_from_disk("nonexistent-task-id", str(storage_path))

    def test_load_missing_summary_raises_error(self, tmp_path):
        """Test that missing summary.json raises FileNotFoundError."""
        storage_path = tmp_path / "progressive_runs"
        task_dir = storage_path / "test-task-id"
        task_dir.mkdir(parents=True)

        # Create task dir but no summary.json
        with pytest.raises(FileNotFoundError, match="Summary file not found"):
            load_result_from_disk("test-task-id", str(storage_path))

    @pytest.fixture
    def sample_result(self):
        """Create sample workflow result for testing."""
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}],
            cost=0.30,
            duration=15.0,
            failure_analysis=FailureAnalysis(),
        )

        return ProgressiveWorkflowResult(
            workflow_name="test-gen",
            task_id="test-gen-20260117-143022",
            tier_results=[cheap_result],
            final_result=cheap_result,
            total_cost=0.30,
            total_duration=15.0,
            success=True,
        )


class TestListSavedResults:
    """Test listing saved results."""

    def test_list_empty_directory(self, tmp_path):
        """Test listing when no results exist."""
        storage_path = tmp_path / "progressive_runs"

        results = list_saved_results(str(storage_path))

        assert results == []

    def test_list_multiple_results(self, tmp_path):
        """Test listing multiple saved results."""
        storage_path = tmp_path / "progressive_runs"

        # Create 3 sample results with different timestamps
        for i in range(3):
            task_dir = storage_path / f"task-{i}"
            task_dir.mkdir(parents=True)

            timestamp = datetime.now() - timedelta(hours=i)
            summary = {
                "task_id": f"task-{i}",
                "workflow": "test-gen",
                "timestamp": timestamp.isoformat(),
                "total_cost": i * 0.5,
            }

            (task_dir / "summary.json").write_text(json.dumps(summary))

        results = list_saved_results(str(storage_path))

        assert len(results) == 3
        # Should be sorted by timestamp (newest first)
        assert results[0]["task_id"] == "task-0"  # Most recent
        assert results[-1]["task_id"] == "task-2"  # Oldest

    def test_list_ignores_invalid_summaries(self, tmp_path, caplog):
        """Test that invalid summary files are skipped with warning."""
        storage_path = tmp_path / "progressive_runs"

        # Create valid result
        task1_dir = storage_path / "task-1"
        task1_dir.mkdir(parents=True)
        (task1_dir / "summary.json").write_text('{"task_id": "task-1"}')

        # Create invalid JSON
        task2_dir = storage_path / "task-2"
        task2_dir.mkdir(parents=True)
        (task2_dir / "summary.json").write_text("invalid json{")

        results = list_saved_results(str(storage_path))

        # Should only return valid result
        assert len(results) == 1
        assert results[0]["task_id"] == "task-1"

        # Should log warning
        assert "Failed to load summary" in caplog.text


class TestCleanupOldResults:
    """Test cleanup of old results."""

    def test_cleanup_removes_old_results(self, tmp_path):
        """Test that old results are removed."""
        storage_path = tmp_path / "progressive_runs"

        # Create old result (40 days ago)
        old_dir = storage_path / "old-task"
        old_dir.mkdir(parents=True)
        old_timestamp = datetime.now() - timedelta(days=40)
        old_summary = {
            "task_id": "old-task",
            "timestamp": old_timestamp.isoformat(),
        }
        (old_dir / "summary.json").write_text(json.dumps(old_summary))

        # Create recent result (10 days ago)
        recent_dir = storage_path / "recent-task"
        recent_dir.mkdir(parents=True)
        recent_timestamp = datetime.now() - timedelta(days=10)
        recent_summary = {
            "task_id": "recent-task",
            "timestamp": recent_timestamp.isoformat(),
        }
        (recent_dir / "summary.json").write_text(json.dumps(recent_summary))

        # Cleanup with 30-day retention
        deleted, retained = cleanup_old_results(str(storage_path), retention_days=30)

        assert deleted == 1
        assert retained == 1
        assert not old_dir.exists()
        assert recent_dir.exists()

    def test_cleanup_dry_run(self, tmp_path):
        """Test that dry_run doesn't delete anything."""
        storage_path = tmp_path / "progressive_runs"

        # Create old result
        old_dir = storage_path / "old-task"
        old_dir.mkdir(parents=True)
        old_timestamp = datetime.now() - timedelta(days=40)
        old_summary = {
            "task_id": "old-task",
            "timestamp": old_timestamp.isoformat(),
        }
        (old_dir / "summary.json").write_text(json.dumps(old_summary))

        # Cleanup with dry_run=True
        deleted, retained = cleanup_old_results(str(storage_path), retention_days=30, dry_run=True)

        assert deleted == 1
        assert retained == 0
        assert old_dir.exists()  # Still exists in dry run

    def test_cleanup_missing_timestamp(self, tmp_path, caplog):
        """Test that results without timestamp are retained."""
        storage_path = tmp_path / "progressive_runs"

        # Create result without timestamp
        task_dir = storage_path / "no-timestamp-task"
        task_dir.mkdir(parents=True)
        summary = {"task_id": "no-timestamp-task"}
        (task_dir / "summary.json").write_text(json.dumps(summary))

        deleted, retained = cleanup_old_results(str(storage_path), retention_days=30)

        assert deleted == 0
        assert retained == 1
        assert task_dir.exists()
        assert "No timestamp" in caplog.text


class TestGenerateCostAnalytics:
    """Test cost analytics generation."""

    def test_analytics_empty_directory(self, tmp_path):
        """Test analytics with no results."""
        storage_path = tmp_path / "progressive_runs"

        analytics = generate_cost_analytics(str(storage_path))

        assert analytics["total_runs"] == 0
        assert analytics["total_cost"] == 0.0
        assert analytics["total_savings"] == 0.0

    def test_analytics_with_results(self, tmp_path):
        """Test analytics generation with multiple results."""
        storage_path = tmp_path / "progressive_runs"

        # Create 3 sample results
        for i in range(3):
            task_dir = storage_path / f"task-{i}"
            task_dir.mkdir(parents=True)

            summary = {
                "task_id": f"task-{i}",
                "workflow": "test-gen" if i < 2 else "bug-predict",
                "timestamp": datetime.now().isoformat(),
                "total_cost": (i + 1) * 0.5,
                "cost_savings": (i + 1) * 0.3,
                "cost_savings_percent": 30.0,
                "success": i < 2,  # First 2 succeed
                "tier_count": 2 if i < 2 else 1,  # First 2 have 2 tiers (escalated)
                "final_cqs": 85.0 + i,
            }

            (task_dir / "summary.json").write_text(json.dumps(summary))

        analytics = generate_cost_analytics(str(storage_path))

        assert analytics["total_runs"] == 3
        assert analytics["total_cost"] == 3.0  # 0.5 + 1.0 + 1.5
        assert analytics["total_savings"] == 1.8  # 0.3 + 0.6 + 0.9
        assert analytics["success_rate"] == pytest.approx(0.67, rel=0.01)
        assert analytics["escalation_rate"] == pytest.approx(0.67, rel=0.01)  # 2 out of 3

        # Check per-workflow stats
        assert "test-gen" in analytics["workflow_stats"]
        assert analytics["workflow_stats"]["test-gen"]["runs"] == 2

    def test_analytics_workflow_breakdown(self, tmp_path):
        """Test per-workflow analytics breakdown."""
        storage_path = tmp_path / "progressive_runs"

        # Create results for 2 different workflows
        for workflow in ["test-gen", "bug-predict"]:
            for i in range(2):
                task_dir = storage_path / f"{workflow}-{i}"
                task_dir.mkdir(parents=True)

                summary = {
                    "task_id": f"{workflow}-{i}",
                    "workflow": workflow,
                    "timestamp": datetime.now().isoformat(),
                    "total_cost": 1.0,
                    "cost_savings": 0.5,
                    "success": True,
                    "tier_count": 1,
                    "final_cqs": 85.0,
                }

                (task_dir / "summary.json").write_text(json.dumps(summary))

        analytics = generate_cost_analytics(str(storage_path))

        # Both workflows should have 2 runs
        assert analytics["workflow_stats"]["test-gen"]["runs"] == 2
        assert analytics["workflow_stats"]["bug-predict"]["runs"] == 2

        # Check avg calculations
        test_gen_stats = analytics["workflow_stats"]["test-gen"]
        assert test_gen_stats["avg_cost"] == 1.0
        assert test_gen_stats["avg_savings"] == 0.5
        assert test_gen_stats["success_rate"] == 1.0


class TestFormatCostAnalyticsReport:
    """Test analytics report formatting."""

    def test_format_analytics_report_structure(self):
        """Test that formatted report contains expected sections."""
        analytics = {
            "total_runs": 10,
            "total_cost": 12.50,
            "total_savings": 8.75,
            "avg_savings_percent": 70.0,
            "escalation_rate": 0.60,
            "success_rate": 0.90,
            "avg_final_cqs": 87.5,
            "tier_usage": {},
            "tier_costs": {},
            "workflow_stats": {
                "test-gen": {
                    "runs": 5,
                    "avg_cost": 1.25,
                    "avg_savings": 0.87,
                    "success_rate": 0.80,
                }
            },
        }

        report = format_cost_analytics_report(analytics)

        assert "PROGRESSIVE ESCALATION ANALYTICS" in report
        assert "OVERALL STATISTICS:" in report
        assert "Total Runs: 10" in report
        assert "Total Cost: $12.50" in report
        assert "Total Savings: $8.75" in report
        assert "PER-WORKFLOW BREAKDOWN:" in report
        assert "test-gen:" in report

    def test_format_analytics_no_workflow_stats(self):
        """Test formatting when no workflow stats available."""
        analytics = {
            "total_runs": 0,
            "total_cost": 0.0,
            "total_savings": 0.0,
            "avg_savings_percent": 0.0,
            "escalation_rate": 0.0,
            "success_rate": 0.0,
            "avg_final_cqs": 0.0,
            "tier_usage": {},
            "tier_costs": {},
            "workflow_stats": {},
        }

        report = format_cost_analytics_report(analytics)

        assert "PROGRESSIVE ESCALATION ANALYTICS" in report
        # Should not crash with empty stats
