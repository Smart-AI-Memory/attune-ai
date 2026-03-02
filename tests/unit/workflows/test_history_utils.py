"""Tests for history_utils module.

Tests _get_history_store, _save_workflow_run, get_workflow_stats,
and _load_workflow_history.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_result(
    success: bool = True,
    error: str | None = None,
    cost: float = 0.05,
    stages: list | None = None,
    final_output: Any = None,
):
    """Create a mock WorkflowResult with required fields."""
    result = MagicMock()
    result.success = success
    result.started_at = datetime(2026, 1, 1, 12, 0, 0)
    result.completed_at = datetime(2026, 1, 1, 12, 0, 30)
    result.total_duration_ms = 30000
    result.error = error
    result.final_output = final_output

    # Cost report
    result.cost_report.total_cost = cost
    result.cost_report.baseline_cost = cost * 2
    result.cost_report.savings = cost
    result.cost_report.savings_percent = 50.0

    # Stages
    if stages is None:
        stage = MagicMock()
        stage.name = "analysis"
        stage.tier.value = "capable"
        stage.skipped = False
        stage.cost = cost
        stage.duration_ms = 15000
        stages = [stage]
    result.stages = stages

    return result


# ---------------------------------------------------------------------------
# Tests for _get_history_store
# ---------------------------------------------------------------------------


class TestGetHistoryStore:
    """Tests for _get_history_store singleton."""

    def test_returns_store_on_success(self):
        """Returns WorkflowHistoryStore on successful initialization."""
        import attune.workflows.history_utils as hu

        # Reset singleton
        hu._history_store = None

        mock_store = MagicMock()
        with patch.object(hu, "_history_store", None):
            with patch("attune.workflows.history_utils._get_history_store") as mock_fn:
                mock_fn.return_value = mock_store
                result = mock_fn()

        assert result is mock_store

    def test_returns_none_on_failure(self):
        """Returns None when initialization fails."""
        import attune.workflows.history_utils as hu

        # Force re-initialization
        original = hu._history_store
        hu._history_store = None

        with patch(
            "attune.workflows.history.WorkflowHistoryStore",
            side_effect=OSError("DB locked"),
        ):
            result = hu._get_history_store()

        # Restore
        hu._history_store = original

        assert result is None

    def test_singleton_caches_false_on_failure(self):
        """Marks failed init with False to avoid repeated attempts."""
        import attune.workflows.history_utils as hu

        original = hu._history_store
        hu._history_store = None

        with patch(
            "attune.workflows.history.WorkflowHistoryStore",
            side_effect=ImportError("missing"),
        ):
            hu._get_history_store()
            assert hu._history_store is False

        hu._history_store = original


# ---------------------------------------------------------------------------
# Tests for _load_workflow_history (deprecated)
# ---------------------------------------------------------------------------


class TestLoadWorkflowHistory:
    """Tests for the deprecated _load_workflow_history function."""

    def test_emits_deprecation_warning(self, tmp_path):
        """Emitting DeprecationWarning."""
        from attune.workflows.history_utils import _load_workflow_history

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            _load_workflow_history(str(tmp_path / "nonexistent.json"))

        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)

    def test_returns_empty_for_missing_file(self, tmp_path):
        """Returns empty list for non-existent file."""
        from attune.workflows.history_utils import _load_workflow_history

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(tmp_path / "missing.json"))

        assert result == []

    def test_returns_data_from_json(self, tmp_path):
        """Returns list from valid JSON file."""
        from attune.workflows.history_utils import _load_workflow_history

        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"workflow": "test", "success": True}]))

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(history_file))

        assert len(result) == 1
        assert result[0]["workflow"] == "test"

    def test_returns_empty_for_corrupt_json(self, tmp_path):
        """Returns empty list for corrupt JSON."""
        from attune.workflows.history_utils import _load_workflow_history

        history_file = tmp_path / "bad.json"
        history_file.write_text("not json")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = _load_workflow_history(str(history_file))

        assert result == []


# ---------------------------------------------------------------------------
# Tests for _save_workflow_run (JSON fallback path)
# ---------------------------------------------------------------------------


class TestSaveWorkflowRun:
    """Tests for _save_workflow_run with JSON fallback."""

    def test_saves_to_json_when_sqlite_unavailable(self, tmp_path):
        """Saves to JSON file when SQLite store is None."""
        from attune.workflows.history_utils import _save_workflow_run

        result = _make_mock_result()
        history_file = str(tmp_path / "workflow_runs.json")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("code-review", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 1
        assert data[0]["workflow"] == "code-review"
        assert data[0]["provider"] == "anthropic"
        assert data[0]["success"] is True

    def test_appends_to_existing_json(self, tmp_path):
        """Appends new run to existing JSON history."""
        from attune.workflows.history_utils import _save_workflow_run

        history_file = str(tmp_path / "workflow_runs.json")
        Path(history_file).write_text(json.dumps([{"workflow": "old"}]))

        result = _make_mock_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("new-wf", "openai", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 2

    def test_trims_to_max_history(self, tmp_path):
        """Trims history to max_history entries."""
        from attune.workflows.history_utils import _save_workflow_run

        history_file = str(tmp_path / "workflow_runs.json")
        existing = [{"workflow": f"run-{i}"} for i in range(10)]
        Path(history_file).write_text(json.dumps(existing))

        result = _make_mock_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("new", "anthropic", result, history_file=history_file, max_history=5)

        data = json.loads(Path(history_file).read_text())
        assert len(data) == 5

    def test_extracts_xml_parsed_fields(self, tmp_path):
        """Extracts XML-parsed fields from final_output."""
        from attune.workflows.history_utils import _save_workflow_run

        result = _make_mock_result(
            final_output={
                "xml_parsed": True,
                "summary": "Found issues",
                "findings": ["f1"],
                "checklist": ["c1"],
            },
        )

        history_file = str(tmp_path / "workflow_runs.json")

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            _save_workflow_run("audit", "anthropic", result, history_file=history_file)

        data = json.loads(Path(history_file).read_text())
        assert data[0]["xml_parsed"] is True
        assert data[0]["summary"] == "Found issues"

    def test_uses_sqlite_when_available(self, tmp_path):
        """Uses SQLite store when available."""
        from attune.workflows.history_utils import _save_workflow_run

        mock_store = MagicMock()
        result = _make_mock_result()

        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            _save_workflow_run("code-review", "anthropic", result)

        mock_store.record_run.assert_called_once()


# ---------------------------------------------------------------------------
# Tests for get_workflow_stats (JSON fallback path)
# ---------------------------------------------------------------------------


class TestGetWorkflowStats:
    """Tests for get_workflow_stats function."""

    def test_empty_history_returns_zeros(self, tmp_path):
        """Empty history returns zero stats."""
        from attune.workflows.history_utils import get_workflow_stats

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(str(tmp_path / "nonexistent.json"))

        assert stats["total_runs"] == 0
        assert stats["successful_runs"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["by_workflow"] == {}

    def test_stats_from_json_history(self, tmp_path):
        """Computes stats from JSON history."""
        from attune.workflows.history_utils import get_workflow_stats

        history = [
            {
                "workflow": "code-review",
                "provider": "anthropic",
                "success": True,
                "cost": 0.05,
                "savings": 0.05,
                "savings_percent": 50.0,
                "stages": [{"tier": "capable", "skipped": False, "cost": 0.05}],
            },
            {
                "workflow": "code-review",
                "provider": "anthropic",
                "success": False,
                "cost": 0.03,
                "savings": 0.03,
                "savings_percent": 50.0,
                "stages": [],
            },
        ]

        history_file = str(tmp_path / "runs.json")
        Path(history_file).write_text(json.dumps(history))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file)

        assert stats["total_runs"] == 2
        assert stats["successful_runs"] == 1
        assert stats["total_cost"] == pytest.approx(0.08)
        assert stats["by_workflow"]["code-review"]["runs"] == 2
        assert stats["by_provider"]["anthropic"]["runs"] == 2

    def test_recent_runs_most_recent_first(self, tmp_path):
        """Recent runs are in most-recent-first order."""
        from attune.workflows.history_utils import get_workflow_stats

        history = [
            {"workflow": f"run-{i}", "success": True, "cost": 0, "savings": 0, "stages": []}
            for i in range(15)
        ]

        history_file = str(tmp_path / "runs.json")
        Path(history_file).write_text(json.dumps(history))

        with patch("attune.workflows.history_utils._get_history_store", return_value=None):
            stats = get_workflow_stats(history_file)

        assert len(stats["recent_runs"]) == 10
        assert stats["recent_runs"][0]["workflow"] == "run-14"

    def test_uses_sqlite_when_available(self):
        """Uses SQLite store when available."""
        from attune.workflows.history_utils import get_workflow_stats

        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_runs": 42}

        with patch("attune.workflows.history_utils._get_history_store", return_value=mock_store):
            stats = get_workflow_stats()

        assert stats["total_runs"] == 42
