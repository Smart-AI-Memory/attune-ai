"""Coverage supplement for src/attune/workflows/history_utils.py

Targets uncovered lines from initial run (79.62%):
- _load_workflow_history() deprecated function (lines 67-83)
- _save_workflow_run() SQLite record_run failure → JSON fallback (lines 112-114)
- JSON load error handling for corrupted history file (lines 127-128)
- XML-parsed final_output fields in run record (lines 157-161)
- get_workflow_stats() SQLite failure → JSON fallback (lines 197-199)
- JSON history read error in get_workflow_stats (lines 210-211)
- Per-tier aggregation across stages (lines 255-259)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.history_utils import (
    _load_workflow_history,
    _save_workflow_run,
    get_workflow_stats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workflow_result(
    success: bool = True,
    cost: float = 0.01,
    savings: float = 0.005,
    savings_percent: float = 33.0,
    error: str | None = None,
    final_output=None,
) -> MagicMock:
    result = MagicMock()
    result.success = success
    result.error = error
    result.total_duration_ms = 1234
    result.started_at.isoformat.return_value = "2026-01-01T00:00:00"
    result.completed_at.isoformat.return_value = "2026-01-01T00:00:01"
    result.cost_report.total_cost = cost
    result.cost_report.baseline_cost = cost + savings
    result.cost_report.savings = savings
    result.cost_report.savings_percent = savings_percent

    stage = MagicMock()
    stage.name = "analyze"
    stage.tier.value = "cheap"
    stage.skipped = False
    stage.cost = cost
    stage.duration_ms = 500
    result.stages = [stage]

    result.final_output = final_output if final_output is not None else "plain text output"
    return result


# ---------------------------------------------------------------------------
# _load_workflow_history() — deprecated API
# ---------------------------------------------------------------------------


class TestLoadWorkflowHistoryDeprecated:
    def test_issues_deprecation_warning(self, tmp_path):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _load_workflow_history(history_file=str(tmp_path / "nonexistent.json"))
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)

    def test_returns_empty_list_when_file_missing(self, tmp_path):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(history_file=str(tmp_path / "none.json"))
        assert result == []

    def test_returns_list_from_existing_json(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"workflow": "wf1"}]))
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(history_file=str(history_file))
        assert len(result) == 1
        assert result[0]["workflow"] == "wf1"

    def test_returns_empty_list_for_corrupted_json(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text("not valid json {{{{")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(history_file=str(history_file))
        assert result == []

    def test_returns_empty_list_when_json_is_not_a_list(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps({"workflow": "wf1"}))
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(history_file=str(history_file))
        assert result == []

    def test_uses_default_history_file_path(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history()
        # Just verifies default path doesn't crash
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _save_workflow_run() — SQLite record_run failure → JSON fallback
# ---------------------------------------------------------------------------


class TestSaveWorkflowRunSQLiteFailure:
    def test_falls_back_to_json_when_record_run_raises(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        mock_store = MagicMock()
        mock_store.record_run.side_effect = OSError("disk full")

        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            _save_workflow_run(
                "wf", "anthropic", _make_workflow_result(), history_file=history_file
            )

        # Should have fallen back to JSON
        assert Path(history_file).exists()
        data = json.loads(Path(history_file).read_text())
        assert len(data) == 1

    def test_falls_back_when_record_run_raises_permission_error(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        mock_store = MagicMock()
        mock_store.record_run.side_effect = PermissionError("denied")

        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            _save_workflow_run(
                "wf", "anthropic", _make_workflow_result(), history_file=history_file
            )

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 1


# ---------------------------------------------------------------------------
# _save_workflow_run() — JSON history file read errors
# ---------------------------------------------------------------------------


class TestSaveWorkflowRunJsonReadErrors:
    def test_corrupted_existing_json_is_ignored(self, tmp_path):
        history_file = tmp_path / "runs.json"
        history_file.write_text("not json {{{{")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run(
                "wf", "anthropic", _make_workflow_result(), history_file=str(history_file)
            )

        data = json.loads(history_file.read_text())
        assert len(data) == 1  # new entry written despite corrupted existing file

    def test_non_list_existing_json_is_ignored(self, tmp_path):
        history_file = tmp_path / "runs.json"
        history_file.write_text(json.dumps({"old": "data"}))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run(
                "wf", "anthropic", _make_workflow_result(), history_file=str(history_file)
            )

        data = json.loads(history_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1


# ---------------------------------------------------------------------------
# _save_workflow_run() — XML-parsed final_output fields
# ---------------------------------------------------------------------------


class TestSaveWorkflowRunXmlOutput:
    def test_xml_parsed_flag_stored_in_run_record(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        final_output = {
            "xml_parsed": True,
            "summary": "All good",
            "findings": ["finding1", "finding2"],
            "checklist": ["check1"],
        }
        result = _make_workflow_result(final_output=final_output)

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        run = data[0]
        assert run.get("xml_parsed") is True
        assert run.get("summary") == "All good"
        assert run.get("findings") == ["finding1", "finding2"]
        assert run.get("checklist") == ["check1"]

    def test_non_xml_output_does_not_store_xml_fields(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result(final_output="plain string output")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        run = data[0]
        assert "xml_parsed" not in run

    def test_dict_without_xml_parsed_key_not_stored(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result(final_output={"plain": "dict"})

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert "xml_parsed" not in data[0]


# ---------------------------------------------------------------------------
# get_workflow_stats() — SQLite failure → JSON fallback
# ---------------------------------------------------------------------------


class TestGetWorkflowStatsSQLiteFailure:
    def test_falls_back_to_json_when_get_stats_raises(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        result = _make_workflow_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("wf", "anthropic", result, history_file=history_file)

        mock_store = MagicMock()
        mock_store.get_stats.side_effect = OSError("db corrupted")
        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            stats = get_workflow_stats(history_file=history_file)

        assert stats["total_runs"] == 1

    def test_falls_back_when_get_stats_raises_value_error(self, tmp_path):
        history_file = str(tmp_path / "runs.json")

        mock_store = MagicMock()
        mock_store.get_stats.side_effect = ValueError("schema mismatch")
        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            stats = get_workflow_stats(history_file=history_file)

        assert "total_runs" in stats


# ---------------------------------------------------------------------------
# get_workflow_stats() — JSON read errors
# ---------------------------------------------------------------------------


class TestGetWorkflowStatsJsonReadError:
    def test_corrupted_json_history_returns_empty_stats(self, tmp_path):
        history_file = tmp_path / "runs.json"
        history_file.write_text("not json {{{")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(history_file))

        assert stats["total_runs"] == 0

    def test_non_list_json_returns_empty_stats(self, tmp_path):
        history_file = tmp_path / "runs.json"
        history_file.write_text(json.dumps({"not": "a list"}))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=str(history_file))

        assert stats["total_runs"] == 0


# ---------------------------------------------------------------------------
# get_workflow_stats() — tier aggregation from stages
# ---------------------------------------------------------------------------


class TestGetWorkflowStatsTierAggregation:
    def _write_history(self, tmp_path, tiers: list[str]) -> str:
        """Write history file with stages at the specified tiers."""
        history_file = str(tmp_path / "runs.json")
        runs = []
        for tier in tiers:
            runs.append(
                {
                    "workflow": "wf",
                    "provider": "anthropic",
                    "success": True,
                    "cost": 0.01,
                    "savings": 0.005,
                    "savings_percent": 33.0,
                    "stages": [{"tier": tier, "skipped": False, "cost": 0.01}],
                }
            )
        Path(history_file).write_text(json.dumps(runs))
        return history_file

    def test_cheap_tier_cost_aggregated(self, tmp_path):
        history_file = self._write_history(tmp_path, ["cheap", "cheap"])
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_file)
        assert stats["by_tier"].get("cheap", 0) == pytest.approx(0.02)

    def test_premium_tier_cost_aggregated(self, tmp_path):
        history_file = self._write_history(tmp_path, ["premium"])
        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_file)
        assert stats["by_tier"].get("premium", 0) == pytest.approx(0.01)

    def test_skipped_stages_not_aggregated(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        runs = [
            {
                "workflow": "wf",
                "provider": "anthropic",
                "success": True,
                "cost": 0.0,
                "savings": 0.0,
                "savings_percent": 0.0,
                "stages": [{"tier": "premium", "skipped": True, "cost": 0.05}],
            }
        ]
        Path(history_file).write_text(json.dumps(runs))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_file)

        # Skipped stage cost should not be counted
        assert stats["by_tier"].get("premium", 0) == pytest.approx(0.0)

    def test_recent_runs_ordered_most_recent_first(self, tmp_path):
        history_file = str(tmp_path / "runs.json")
        runs = [
            {
                "workflow": f"wf-{i}",
                "provider": "a",
                "success": True,
                "cost": 0,
                "savings": 0,
                "savings_percent": 0,
                "stages": [],
            }
            for i in range(5)
        ]
        Path(history_file).write_text(json.dumps(runs))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file=history_file)

        recent = stats["recent_runs"]
        # Most recent first: last run (wf-4) should appear first
        assert recent[0]["workflow"] == "wf-4"
