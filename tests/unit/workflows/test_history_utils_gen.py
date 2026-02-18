"""Unit tests for src/attune/workflows/history_utils.py

Tests cover:
- WORKFLOW_HISTORY_FILE constant
- _get_history_store() singleton (returns store or None on failure)
- _save_workflow_run(workflow_name, provider, result, history_file, max_history)
- get_workflow_stats(history_file) — structure and content

Key corrections vs naive generation:
- No save_workflow_run() public function — it's _save_workflow_run()
- No query_workflow_runs() function — it doesn't exist
- _get_history_store() takes NO arguments — it returns a singleton
- _save_workflow_run() takes a WorkflowResult object, NOT a plain dict
- get_workflow_stats() returns a dict with specific keys:
    total_runs, successful_runs, by_workflow, by_provider, by_tier,
    recent_runs, total_cost, total_savings, avg_savings_percent
- When SQLite fails, history falls back to JSON
- _load_workflow_history() is DEPRECATED — not the primary API
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.history_utils import (
    WORKFLOW_HISTORY_FILE,
    _get_history_store,
    _save_workflow_run,
    get_workflow_stats,
)

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_workflow_result(
    success: bool = True,
    cost: float = 0.01,
    savings: float = 0.005,
    savings_percent: float = 33.0,
    error: str | None = None,
) -> MagicMock:
    """Build a minimal WorkflowResult-like mock."""
    result = MagicMock()
    result.success = success
    result.error = error
    result.total_duration_ms = 1234

    # started_at / completed_at must produce .isoformat()
    result.started_at.isoformat.return_value = "2026-01-01T00:00:00"
    result.completed_at.isoformat.return_value = "2026-01-01T00:00:01"

    # cost_report
    result.cost_report.total_cost = cost
    result.cost_report.baseline_cost = cost + savings
    result.cost_report.savings = savings
    result.cost_report.savings_percent = savings_percent

    # stages — each stage must have .name, .tier.value, .skipped, .cost, .duration_ms
    stage = MagicMock()
    stage.name = "analyze"
    stage.tier.value = "cheap"
    stage.skipped = False
    stage.cost = cost
    stage.duration_ms = 500
    result.stages = [stage]

    # final_output — plain string so XML branch is skipped
    result.final_output = "analysis complete"

    return result


# ---------------------------------------------------------------------------
# 1. Module constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_workflow_history_file_is_string(self):
        assert isinstance(WORKFLOW_HISTORY_FILE, str)

    def test_workflow_history_file_references_attune_dir(self):
        assert ".attune" in WORKFLOW_HISTORY_FILE

    def test_workflow_history_file_is_json(self):
        assert WORKFLOW_HISTORY_FILE.endswith(".json")


# ---------------------------------------------------------------------------
# 2. _get_history_store()
# ---------------------------------------------------------------------------


class TestGetHistoryStore:
    def test_returns_without_raising(self):
        """_get_history_store() may return a store or None — never raises."""
        result = _get_history_store()
        # Result is either a store object or None
        assert result is None or result is not None

    def test_no_arguments_required(self):
        """_get_history_store() must be callable with zero arguments."""
        _get_history_store()  # must not raise TypeError

    def test_returns_same_object_on_repeated_calls(self):
        """Singleton: repeated calls return identical object."""
        r1 = _get_history_store()
        r2 = _get_history_store()
        assert r1 is r2

    def test_returns_none_when_sqlite_unavailable(self):
        """When SQLite init fails, store should be None."""
        import attune.workflows.history_utils as hu

        original = hu._history_store
        hu._history_store = None
        try:
            # WorkflowHistoryStore is imported from .history inside the function,
            # so patch it on the history module to make instantiation fail.
            with patch(
                "attune.workflows.history.WorkflowHistoryStore",
                side_effect=OSError("disk unavailable"),
            ):
                result = _get_history_store()
            assert result is None
        finally:
            hu._history_store = original


# ---------------------------------------------------------------------------
# 3. _save_workflow_run() — JSON fallback path
# ---------------------------------------------------------------------------


class TestSaveWorkflowRunJsonFallback:
    """Test _save_workflow_run() using the JSON fallback (no SQLite)."""

    def test_creates_json_file_when_none_exists(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("my-wf", "anthropic", result, history_file=history_file)

        assert Path(history_file).exists()

    def test_saved_json_is_valid_list(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert isinstance(data, list)

    def test_saved_record_contains_workflow_name(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("analyze-code", "openai", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["workflow"] == "analyze-code"

    def test_saved_record_contains_provider(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "openai", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["provider"] == "openai"

    def test_saved_record_contains_success_field(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result(success=True)

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["success"] is True

    def test_failed_result_stored_correctly(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result(success=False, error="timeout")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["success"] is False

    def test_appends_to_existing_history(self, tmp_path):
        history_file = str(tmp_path / "runs.json")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run(
                "wf1", "anthropic", _make_workflow_result(), history_file=history_file
            )
            _save_workflow_run("wf2", "openai", _make_workflow_result(), history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 2

    def test_max_history_trims_old_entries(self, tmp_path):
        history_file = str(tmp_path / "runs.json")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            for i in range(5):
                _save_workflow_run(
                    f"wf-{i}",
                    "anthropic",
                    _make_workflow_result(),
                    history_file=history_file,
                    max_history=3,
                )

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 3

    def test_saves_cost_data(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result(cost=0.05)

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["cost"] == pytest.approx(0.05)

    def test_creates_parent_directories(self, tmp_path):
        nested_dir = tmp_path / "deep" / "nested"
        history_file = str(nested_dir / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        assert Path(history_file).exists()


# ---------------------------------------------------------------------------
# 4. get_workflow_stats() — empty state
# ---------------------------------------------------------------------------


class TestGetWorkflowStatsEmpty:
    def test_returns_dict(self, tmp_path):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(tmp_path / "missing.json"))
        assert isinstance(stats, dict)

    def test_total_runs_is_zero_when_empty(self, tmp_path):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(tmp_path / "none.json"))
        assert stats["total_runs"] == 0

    def test_all_required_keys_present_when_empty(self, tmp_path):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(tmp_path / "none.json"))
        required_keys = {
            "total_runs",
            "successful_runs",
            "by_workflow",
            "by_provider",
            "by_tier",
            "recent_runs",
            "total_cost",
            "total_savings",
            "avg_savings_percent",
        }
        assert required_keys <= set(stats.keys())

    def test_total_cost_is_zero_when_empty(self, tmp_path):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(tmp_path / "none.json"))
        assert stats["total_cost"] == 0.0

    def test_by_tier_dict_present_when_empty(self, tmp_path):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(tmp_path / "none.json"))
        assert isinstance(stats["by_tier"], dict)


# ---------------------------------------------------------------------------
# 5. get_workflow_stats() — with data
# ---------------------------------------------------------------------------


class TestGetWorkflowStatsWithData:
    @pytest.fixture
    def history_with_two_runs(self, tmp_path) -> str:
        """Write a JSON history file with 2 runs and return the path."""
        history_file = str(tmp_path / "runs.json")
        result_ok = _make_workflow_result(
            success=True, cost=0.01, savings=0.005, savings_percent=33.0
        )
        result_fail = _make_workflow_result(
            success=False, cost=0.02, savings=0.0, savings_percent=0.0
        )

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf-a", "anthropic", result_ok, history_file=history_file)
            _save_workflow_run("wf-b", "openai", result_fail, history_file=history_file)

        return history_file

    def test_total_runs_reflects_saved_count(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert stats["total_runs"] == 2

    def test_successful_runs_counted_correctly(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert stats["successful_runs"] == 1

    def test_by_workflow_contains_saved_workflows(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert "wf-a" in stats["by_workflow"]
        assert "wf-b" in stats["by_workflow"]

    def test_by_provider_contains_saved_providers(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert "anthropic" in stats["by_provider"]
        assert "openai" in stats["by_provider"]

    def test_total_cost_is_sum_of_all_runs(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert stats["total_cost"] == pytest.approx(0.03)

    def test_recent_runs_is_list(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        assert isinstance(stats["recent_runs"], list)

    def test_recent_runs_max_10_entries(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            for i in range(15):
                _save_workflow_run(
                    f"wf-{i}", "anthropic", _make_workflow_result(), history_file=history_file
                )
            stats = get_workflow_stats(history_file=history_file)
        assert len(stats["recent_runs"]) <= 10

    def test_by_workflow_run_count(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            for _ in range(3):
                _save_workflow_run(
                    "my-wf", "anthropic", _make_workflow_result(), history_file=history_file
                )
            stats = get_workflow_stats(history_file=history_file)
        assert stats["by_workflow"]["my-wf"]["runs"] == 3

    def test_avg_savings_percent_computed(self, history_with_two_runs):
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_with_two_runs)
        # Should be a float (only successful runs contribute to avg)
        assert isinstance(stats["avg_savings_percent"], float)


# ---------------------------------------------------------------------------
# 6. SQLite store path
# ---------------------------------------------------------------------------


class TestSQLitePath:
    def test_save_uses_sqlite_store_when_available(self, tmp_path):
        """When store is available, record_run is called instead of JSON."""
        mock_store = MagicMock()
        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            _save_workflow_run("wf", "anthropic", _make_workflow_result())
        mock_store.record_run.assert_called_once()

    def test_get_stats_uses_sqlite_when_available(self):
        """When store is available, store.get_stats() is called."""
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {
            "total_runs": 5,
            "successful_runs": 4,
            "by_workflow": {},
            "by_provider": {},
            "by_tier": {},
            "recent_runs": [],
            "total_cost": 0.1,
            "total_savings": 0.05,
            "avg_savings_percent": 33.0,
        }
        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            stats = get_workflow_stats()
        assert stats["total_runs"] == 5
        mock_store.get_stats.assert_called_once()
