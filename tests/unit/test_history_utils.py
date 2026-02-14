"""Tests for attune.workflows.history_utils module."""

import json
import warnings
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage
from attune.workflows.history_utils import (
    _load_workflow_history,
    _save_workflow_run,
    get_workflow_stats,
)


def _make_result(
    success: bool = True, cost: float = 0.01, savings: float = 0.005
) -> WorkflowResult:
    """Create a minimal WorkflowResult for testing."""
    now = datetime.now()
    return WorkflowResult(
        success=success,
        final_output="test output",
        stages=[
            WorkflowStage(
                name="stage1",
                tier=MagicMock(value="cheap"),
                description="test stage",
                skipped=False,
                cost=cost,
                duration_ms=100,
                result="ok",
            ),
        ],
        cost_report=CostReport(
            total_cost=cost,
            baseline_cost=cost + savings,
            savings=savings,
            savings_percent=50.0,
        ),
        started_at=now - timedelta(seconds=5),
        completed_at=now,
        total_duration_ms=5000,
        error=None,
    )


class TestLoadWorkflowHistory:
    def test_returns_empty_list_when_no_file(self, tmp_path):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = _load_workflow_history(str(tmp_path / "nonexistent.json"))
        assert result == []

    def test_returns_list_from_valid_json(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"workflow": "test", "success": True}]))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = _load_workflow_history(str(history_file))
        assert len(result) == 1
        assert result[0]["workflow"] == "test"

    def test_returns_empty_on_malformed_json(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text("{bad json")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = _load_workflow_history(str(history_file))
        assert result == []

    def test_returns_empty_on_non_list_json(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps({"not": "a list"}))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            result = _load_workflow_history(str(history_file))
        assert result == []

    def test_emits_deprecation_warning(self, tmp_path):
        with pytest.warns(DeprecationWarning, match="deprecated"):
            _load_workflow_history(str(tmp_path / "nonexistent.json"))


class TestSaveWorkflowRun:
    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_saves_to_json_fallback(self, mock_store, tmp_path):
        history_file = tmp_path / "history.json"
        result = _make_result()
        _save_workflow_run("test-wf", "anthropic", result, str(history_file))

        assert history_file.exists()
        data = json.loads(history_file.read_text())
        assert len(data) == 1
        assert data[0]["workflow"] == "test-wf"
        assert data[0]["provider"] == "anthropic"
        assert data[0]["success"] is True

    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_appends_to_existing_history(self, mock_store, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"workflow": "old", "success": True}]))

        result = _make_result()
        _save_workflow_run("new-wf", "openai", result, str(history_file))

        data = json.loads(history_file.read_text())
        assert len(data) == 2
        assert data[0]["workflow"] == "old"
        assert data[1]["workflow"] == "new-wf"

    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_trims_history_to_max(self, mock_store, tmp_path):
        history_file = tmp_path / "history.json"
        existing = [{"workflow": f"run-{i}", "success": True} for i in range(100)]
        history_file.write_text(json.dumps(existing))

        result = _make_result()
        _save_workflow_run("latest", "anthropic", result, str(history_file), max_history=50)

        data = json.loads(history_file.read_text())
        assert len(data) == 50
        assert data[-1]["workflow"] == "latest"

    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_saves_xml_parsed_fields(self, mock_store, tmp_path):
        history_file = tmp_path / "history.json"
        result = _make_result()
        result.final_output = {
            "xml_parsed": True,
            "summary": "Test summary",
            "findings": [{"severity": "high"}],
            "checklist": ["item1"],
        }
        _save_workflow_run("wf", "anthropic", result, str(history_file))

        data = json.loads(history_file.read_text())
        assert data[0]["xml_parsed"] is True
        assert data[0]["summary"] == "Test summary"
        assert len(data[0]["findings"]) == 1

    @patch("attune.workflows.history_utils._get_history_store")
    def test_uses_sqlite_when_available(self, mock_get_store):
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        result = _make_result()
        _save_workflow_run("wf", "anthropic", result)
        mock_store.record_run.assert_called_once()


class TestGetWorkflowStats:
    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_empty_history(self, mock_store, tmp_path):
        stats = get_workflow_stats(str(tmp_path / "nonexistent.json"))
        assert stats["total_runs"] == 0
        assert stats["successful_runs"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["avg_savings_percent"] == 0.0

    @patch("attune.workflows.history_utils._get_history_store", return_value=None)
    def test_aggregates_stats(self, mock_store, tmp_path):
        history_file = tmp_path / "history.json"
        runs = [
            {
                "workflow": "security",
                "provider": "anthropic",
                "success": True,
                "cost": 0.05,
                "savings": 0.02,
                "savings_percent": 40.0,
                "stages": [{"tier": "cheap", "skipped": False, "cost": 0.03}],
            },
            {
                "workflow": "security",
                "provider": "openai",
                "success": True,
                "cost": 0.10,
                "savings": 0.05,
                "savings_percent": 50.0,
                "stages": [{"tier": "capable", "skipped": False, "cost": 0.08}],
            },
            {
                "workflow": "review",
                "provider": "anthropic",
                "success": False,
                "cost": 0.01,
                "savings": 0.0,
                "stages": [],
            },
        ]
        history_file.write_text(json.dumps(runs))

        stats = get_workflow_stats(str(history_file))
        assert stats["total_runs"] == 3
        assert stats["successful_runs"] == 2
        assert stats["by_workflow"]["security"]["runs"] == 2
        assert stats["by_workflow"]["review"]["runs"] == 1
        assert stats["by_provider"]["anthropic"]["runs"] == 2
        assert stats["by_provider"]["openai"]["runs"] == 1
        assert stats["by_tier"]["cheap"] == pytest.approx(0.03)
        assert stats["by_tier"]["capable"] == pytest.approx(0.08)
        assert stats["total_cost"] == pytest.approx(0.16)
        assert stats["total_savings"] == pytest.approx(0.07)
        assert stats["avg_savings_percent"] == pytest.approx(45.0)
        assert len(stats["recent_runs"]) == 3

    @patch("attune.workflows.history_utils._get_history_store")
    def test_uses_sqlite_when_available(self, mock_get_store):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_runs": 42}
        mock_get_store.return_value = mock_store
        stats = get_workflow_stats()
        assert stats["total_runs"] == 42
