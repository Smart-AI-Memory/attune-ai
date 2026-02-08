"""Tests for SQLite-based workflow history storage.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from attune.workflows.base import CostReport, ModelTier, WorkflowResult, WorkflowStage
from attune.workflows.history import WorkflowHistoryStore


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def store(temp_db):
    """Create a WorkflowHistoryStore for testing."""
    store = WorkflowHistoryStore(temp_db)
    yield store
    store.close()


@pytest.fixture
def sample_result():
    """Create a sample WorkflowResult for testing."""
    stages = [
        WorkflowStage(
            name="analyze",
            tier=ModelTier.CHEAP,
            description="Analyze input",
            skipped=False,
            cost=0.001,
            duration_ms=1000,
            input_tokens=100,
            output_tokens=50,
            skip_reason=None,
        ),
        WorkflowStage(
            name="generate",
            tier=ModelTier.CAPABLE,
            description="Generate output",
            skipped=False,
            cost=0.015,
            duration_ms=2000,
            input_tokens=500,
            output_tokens=300,
            skip_reason=None,
        ),
        WorkflowStage(
            name="review",
            tier=ModelTier.PREMIUM,
            description="Review results",
            skipped=True,
            cost=0.0,
            duration_ms=0,
            input_tokens=0,
            output_tokens=0,
            skip_reason="Not needed",
        ),
    ]

    result = WorkflowResult(
        success=True,
        stages=stages,
        final_output={"result": "success"},
        cost_report=CostReport(
            total_cost=0.016,
            baseline_cost=0.050,
            savings=0.034,
            savings_percent=68.0,
            by_tier={"cheap": 0.001, "capable": 0.015, "premium": 0.0},
            savings_from_cache=0.0,
        ),
        started_at=datetime.now(),
        completed_at=datetime.now() + timedelta(seconds=3),
        total_duration_ms=3000,
        provider="anthropic",
        error=None,
    )

    return result


class TestWorkflowHistoryStore:
    """Test suite for WorkflowHistoryStore."""

    def test_init_creates_database(self, temp_db):
        """Test that initialization creates database file."""
        # temp_db fixture creates the file, so just verify store can be created
        store = WorkflowHistoryStore(temp_db)

        assert Path(temp_db).exists()
        store.close()

    def test_init_creates_schema(self, store):
        """Test that initialization creates required tables."""
        cursor = store.conn.cursor()

        # Check tables exist
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
        """
        )
        tables = {row["name"] for row in cursor.fetchall()}

        assert "workflow_runs" in tables
        assert "workflow_stages" in tables

    def test_init_creates_indexes(self, store):
        """Test that initialization creates indexes."""
        cursor = store.conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_%'
        """
        )
        indexes = {row["name"] for row in cursor.fetchall()}

        assert "idx_workflow_name" in indexes
        assert "idx_started_at" in indexes
        assert "idx_provider" in indexes
        assert "idx_success" in indexes
        assert "idx_run_stages" in indexes

    def test_record_run_inserts_run(self, store, sample_result):
        """Test recording a workflow run."""
        run_id = "test-run-1"

        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        # Verify run was inserted
        cursor = store.conn.cursor()
        cursor.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,))
        run = cursor.fetchone()

        assert run is not None
        assert run["workflow_name"] == "test-workflow"
        assert run["provider"] == "anthropic"
        assert run["success"] == 1
        assert run["total_cost"] == 0.016
        assert run["savings"] == 0.034
        assert run["savings_percent"] == 68.0

    def test_record_run_inserts_stages(self, store, sample_result):
        """Test recording workflow stages."""
        run_id = "test-run-1"

        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        # Verify stages were inserted
        cursor = store.conn.cursor()
        cursor.execute(
            "SELECT * FROM workflow_stages WHERE run_id = ? ORDER BY stage_id", (run_id,)
        )
        stages = cursor.fetchall()

        assert len(stages) == 3
        assert stages[0]["stage_name"] == "analyze"
        assert stages[0]["tier"] == "cheap"
        assert stages[0]["skipped"] == 0
        assert stages[1]["stage_name"] == "generate"
        assert stages[2]["stage_name"] == "review"
        assert stages[2]["skipped"] == 1
        assert stages[2]["skip_reason"] == "Not needed"

    def test_record_run_duplicate_id_raises_error(self, store, sample_result):
        """Test that duplicate run_id raises ValueError."""
        run_id = "test-run-1"

        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        # Try to insert same run_id again
        with pytest.raises(ValueError, match="Duplicate run_id"):
            store.record_run(run_id, "test-workflow", "anthropic", sample_result)

    def test_query_runs_returns_all_runs(self, store, sample_result):
        """Test querying all runs."""
        # Insert multiple runs with incrementing timestamps
        import time

        for i in range(5):
            # Add small delay to ensure different timestamps
            time.sleep(0.01)
            result = WorkflowResult(
                **{
                    **sample_result.__dict__,
                    "started_at": datetime.now(),
                    "completed_at": datetime.now(),
                }
            )
            store.record_run(f"run-{i}", "test-workflow", "anthropic", result)

        runs = store.query_runs()

        assert len(runs) == 5
        # Verify most recent first (run-4 was inserted last)
        assert runs[0]["run_id"] == "run-4"
        assert runs[-1]["run_id"] == "run-0"

    def test_query_runs_filter_by_workflow(self, store, sample_result):
        """Test filtering runs by workflow name."""
        store.record_run("run-1", "workflow-a", "anthropic", sample_result)
        store.record_run("run-2", "workflow-b", "anthropic", sample_result)
        store.record_run("run-3", "workflow-a", "anthropic", sample_result)

        runs = store.query_runs(workflow_name="workflow-a")

        assert len(runs) == 2
        assert all(r["workflow_name"] == "workflow-a" for r in runs)

    def test_query_runs_filter_by_provider(self, store, sample_result):
        """Test filtering runs by provider."""
        store.record_run("run-1", "test-workflow", "anthropic", sample_result)
        store.record_run("run-2", "test-workflow", "openai", sample_result)
        store.record_run("run-3", "test-workflow", "anthropic", sample_result)

        runs = store.query_runs(provider="anthropic")

        assert len(runs) == 2
        assert all(r["provider"] == "anthropic" for r in runs)

    def test_query_runs_filter_by_date_range(self, store, sample_result):
        """Test filtering runs by date range."""
        now = datetime.now()

        # Create results with different timestamps
        old_result = WorkflowResult(
            **{
                **sample_result.__dict__,
                "started_at": now - timedelta(days=10),
                "completed_at": now - timedelta(days=10),
            }
        )

        recent_result = WorkflowResult(
            **{
                **sample_result.__dict__,
                "started_at": now - timedelta(days=1),
                "completed_at": now - timedelta(days=1),
            }
        )

        store.record_run("old-run", "test-workflow", "anthropic", old_result)
        store.record_run("recent-run", "test-workflow", "anthropic", recent_result)

        # Query runs from last 5 days
        since = now - timedelta(days=5)
        runs = store.query_runs(since=since)

        assert len(runs) == 1
        assert runs[0]["run_id"] == "recent-run"

    def test_query_runs_success_only(self, store):
        """Test filtering for successful runs only."""
        # Successful run
        success_result = WorkflowResult(
            success=True,
            stages=[],
            final_output={},
            cost_report=CostReport(
                total_cost=0.01,
                baseline_cost=0.05,
                savings=0.04,
                savings_percent=80.0,
                by_tier={},
                savings_from_cache=0.0,
            ),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_duration_ms=1000,
            provider="anthropic",
            error=None,
            error_type=None,
            transient=False,
        )

        # Failed run - create new instance with modified fields
        failed_result = WorkflowResult(
            success=False,
            stages=[],
            final_output={},
            cost_report=success_result.cost_report,
            started_at=success_result.started_at,
            completed_at=success_result.completed_at,
            total_duration_ms=1000,
            provider="anthropic",
            error="Test error",
            error_type="validation",
            transient=False,
        )

        store.record_run("success-run", "test-workflow", "anthropic", success_result)
        store.record_run("failed-run", "test-workflow", "anthropic", failed_result)

        runs = store.query_runs(success_only=True)

        assert len(runs) == 1
        assert runs[0]["run_id"] == "success-run"
        assert runs[0]["success"] == 1

    def test_query_runs_includes_stages(self, store, sample_result):
        """Test that queried runs include stage data."""
        store.record_run("run-1", "test-workflow", "anthropic", sample_result)

        runs = store.query_runs()

        assert len(runs) == 1
        assert "stages" in runs[0]
        assert len(runs[0]["stages"]) == 3
        assert runs[0]["stages"][0]["stage_name"] == "analyze"

    def test_get_stats_empty_database(self, store):
        """Test get_stats on empty database."""
        stats = store.get_stats()

        assert stats["total_runs"] == 0
        assert stats["successful_runs"] == 0
        assert stats["by_workflow"] == {}
        assert stats["by_provider"] == {}
        assert stats["by_tier"] == {}
        assert stats["recent_runs"] == []
        assert stats["total_cost"] == 0.0
        assert stats["total_savings"] == 0.0
        assert stats["avg_savings_percent"] == 0.0

    def test_get_stats_aggregates_correctly(self, store, sample_result):
        """Test that get_stats aggregates data correctly."""
        # Insert 3 runs
        for i in range(3):
            store.record_run(f"run-{i}", "test-workflow", "anthropic", sample_result)

        stats = store.get_stats()

        assert stats["total_runs"] == 3
        assert stats["successful_runs"] == 3
        assert stats["total_cost"] == pytest.approx(0.048)  # 0.016 * 3
        assert stats["total_savings"] == pytest.approx(0.102)  # 0.034 * 3
        assert stats["avg_savings_percent"] == pytest.approx(68.0)

    def test_get_stats_by_workflow(self, store, sample_result):
        """Test get_stats aggregates by workflow."""
        store.record_run("run-1", "workflow-a", "anthropic", sample_result)
        store.record_run("run-2", "workflow-b", "anthropic", sample_result)
        store.record_run("run-3", "workflow-a", "anthropic", sample_result)

        stats = store.get_stats()

        assert "workflow-a" in stats["by_workflow"]
        assert "workflow-b" in stats["by_workflow"]
        assert stats["by_workflow"]["workflow-a"]["runs"] == 2
        assert stats["by_workflow"]["workflow-b"]["runs"] == 1

    def test_get_stats_by_provider(self, store, sample_result):
        """Test get_stats aggregates by provider."""
        store.record_run("run-1", "test-workflow", "anthropic", sample_result)
        store.record_run("run-2", "test-workflow", "openai", sample_result)
        store.record_run("run-3", "test-workflow", "anthropic", sample_result)

        stats = store.get_stats()

        assert "anthropic" in stats["by_provider"]
        assert "openai" in stats["by_provider"]
        assert stats["by_provider"]["anthropic"]["runs"] == 2
        assert stats["by_provider"]["openai"]["runs"] == 1

    def test_get_stats_by_tier(self, store, sample_result):
        """Test get_stats aggregates by tier."""
        store.record_run("run-1", "test-workflow", "anthropic", sample_result)

        stats = store.get_stats()

        assert "cheap" in stats["by_tier"]
        assert "capable" in stats["by_tier"]
        assert stats["by_tier"]["cheap"] == pytest.approx(0.001)
        assert stats["by_tier"]["capable"] == pytest.approx(0.015)

    def test_get_stats_recent_runs(self, store, sample_result):
        """Test get_stats returns recent runs."""
        # Insert 15 runs with incrementing timestamps
        import time

        for i in range(15):
            time.sleep(0.01)  # Ensure different timestamps
            result = WorkflowResult(
                **{
                    **sample_result.__dict__,
                    "started_at": datetime.now(),
                    "completed_at": datetime.now(),
                }
            )
            store.record_run(f"run-{i}", "test-workflow", "anthropic", result)

        stats = store.get_stats()

        # Should only return 10 most recent
        assert len(stats["recent_runs"]) == 10
        # Most recent first (run-14 was inserted last)
        assert stats["recent_runs"][0]["run_id"] == "run-14"

    def test_get_run_by_id_exists(self, store, sample_result):
        """Test getting a specific run by ID."""
        run_id = "test-run-1"
        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        run = store.get_run_by_id(run_id)

        assert run is not None
        assert run["run_id"] == run_id
        assert run["workflow_name"] == "test-workflow"
        assert len(run["stages"]) == 3

    def test_get_run_by_id_not_found(self, store):
        """Test getting a non-existent run."""
        run = store.get_run_by_id("nonexistent")

        assert run is None

    def test_delete_run_exists(self, store, sample_result):
        """Test deleting an existing run."""
        run_id = "test-run-1"
        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        deleted = store.delete_run(run_id)

        assert deleted is True
        assert store.get_run_by_id(run_id) is None

    def test_delete_run_deletes_stages(self, store, sample_result):
        """Test that deleting a run also deletes stages."""
        run_id = "test-run-1"
        store.record_run(run_id, "test-workflow", "anthropic", sample_result)

        store.delete_run(run_id)

        # Verify stages are deleted
        cursor = store.conn.cursor()
        cursor.execute("SELECT * FROM workflow_stages WHERE run_id = ?", (run_id,))
        stages = cursor.fetchall()

        assert len(stages) == 0

    def test_delete_run_not_found(self, store):
        """Test deleting a non-existent run."""
        deleted = store.delete_run("nonexistent")

        assert deleted is False

    def test_cleanup_old_runs(self, store):
        """Test cleaning up old runs."""
        now = datetime.now()

        # Create old and recent results
        old_result = WorkflowResult(
            success=True,
            stages=[],
            final_output={},
            cost_report=CostReport(
                total_cost=0.01,
                baseline_cost=0.05,
                savings=0.04,
                savings_percent=80.0,
                by_tier={},
                savings_from_cache=0.0,
            ),
            started_at=now - timedelta(days=100),
            completed_at=now - timedelta(days=100),
            total_duration_ms=1000,
            provider="anthropic",
            error=None,
            error_type=None,
            transient=False,
        )

        recent_result = WorkflowResult(
            success=True,
            stages=[],
            final_output={},
            cost_report=old_result.cost_report,
            started_at=now - timedelta(days=10),
            completed_at=now - timedelta(days=10),
            total_duration_ms=1000,
            provider="anthropic",
            error=None,
            error_type=None,
            transient=False,
        )

        store.record_run("old-run", "test-workflow", "anthropic", old_result)
        store.record_run("recent-run", "test-workflow", "anthropic", recent_result)

        # Cleanup runs older than 90 days
        deleted = store.cleanup_old_runs(keep_days=90)

        assert deleted == 1
        assert store.get_run_by_id("old-run") is None
        assert store.get_run_by_id("recent-run") is not None

    def test_context_manager(self, temp_db, sample_result):
        """Test using store as context manager."""
        with WorkflowHistoryStore(temp_db) as store:
            store.record_run("run-1", "test-workflow", "anthropic", sample_result)

            runs = store.query_runs()
            assert len(runs) == 1

        # Connection should be closed after context manager exit
        # Verify by trying to query (should raise error)
        with pytest.raises(sqlite3.ProgrammingError):
            store.query_runs()

    def test_concurrent_writes(self, temp_db, sample_result):
        """Test that SQLite handles concurrent writes correctly."""
        # Create two separate connections
        store1 = WorkflowHistoryStore(temp_db)
        store2 = WorkflowHistoryStore(temp_db)

        try:
            # Write from both connections
            store1.record_run("run-1", "test-workflow", "anthropic", sample_result)
            store2.record_run("run-2", "test-workflow", "anthropic", sample_result)

            # Both should be visible from either connection
            runs1 = store1.query_runs()
            runs2 = store2.query_runs()

            assert len(runs1) == 2
            assert len(runs2) == 2

        finally:
            store1.close()
            store2.close()
