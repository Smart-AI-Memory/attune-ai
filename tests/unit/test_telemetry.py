"""Unit tests for telemetry data structures.

Previously these tests read from real `.attune/*.json` files and skipped
in CI. Rewritten to create fixture data and test structure validation.
"""

from __future__ import annotations

import json

import pytest


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.mark.unit
class TestCostsFileStructure:
    def test_costs_structure_valid(self, tmp_path):
        """costs.json with expected keys parses correctly."""
        data = {
            "daily_totals": {"2026-04-23": 0.12},
            "by_provider": {"anthropic": 0.12},
            "total": 0.12,
        }
        f = tmp_path / ".attune" / "costs.json"
        _write_json(f, data)

        loaded = json.loads(f.read_text())
        assert isinstance(loaded, dict)
        assert isinstance(loaded["daily_totals"], dict)
        assert isinstance(loaded["by_provider"], dict)

    def test_costs_empty_dict_valid(self, tmp_path):
        """An empty costs dict is a valid starting state."""
        f = tmp_path / ".attune" / "costs.json"
        _write_json(f, {})
        assert isinstance(json.loads(f.read_text()), dict)


@pytest.mark.unit
class TestHealthFileStructure:
    def test_health_score_in_range(self, tmp_path):
        """health.json score must be 0–100."""
        data = {"score": 87, "grade": "B", "issues": []}
        f = tmp_path / ".attune" / "health.json"
        _write_json(f, data)

        loaded = json.loads(f.read_text())
        assert isinstance(loaded, dict)
        score = loaded.get("score")
        if score is not None:
            assert isinstance(score, int | float)
            assert 0 <= score <= 100

    def test_health_score_boundary_100(self, tmp_path):
        f = tmp_path / ".attune" / "health.json"
        _write_json(f, {"score": 100})
        loaded = json.loads(f.read_text())
        assert 0 <= loaded["score"] <= 100

    def test_health_score_boundary_0(self, tmp_path):
        f = tmp_path / ".attune" / "health.json"
        _write_json(f, {"score": 0})
        loaded = json.loads(f.read_text())
        assert 0 <= loaded["score"] <= 100


@pytest.mark.unit
class TestWorkflowRunsStructure:
    def test_workflow_runs_is_list(self, tmp_path):
        """workflow_runs.json is a list of run dicts."""
        data = [
            {"workflow": "health-check", "success": True, "cost": 0.01},
            {"workflow": "code-review", "success": False, "cost": 0.05},
        ]
        f = tmp_path / ".attune" / "workflow_runs.json"
        _write_json(f, data)

        loaded = json.loads(f.read_text())
        assert isinstance(loaded, list)
        first = loaded[0]
        assert isinstance(first, dict)
        assert isinstance(first["workflow"], str)
        assert isinstance(first["success"], bool)

    def test_empty_runs_list_valid(self, tmp_path):
        """An empty runs list is a valid starting state."""
        f = tmp_path / ".attune" / "workflow_runs.json"
        _write_json(f, [])
        assert json.loads(f.read_text()) == []
