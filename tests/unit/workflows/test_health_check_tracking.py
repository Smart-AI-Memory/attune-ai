"""Tests for health_check_tracking module.

Tests get_trend_comparison, save_tracking_history, and save_health_json.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# Minimal stubs for HealthCheckReport and CategoryScore
@dataclass
class FakeCategoryScore:
    name: str
    score: float
    weight: float = 1.0
    raw_metrics: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class FakeHealthCheckReport:
    overall_health_score: float
    grade: str
    category_scores: list[FakeCategoryScore]
    timestamp: str = "2026-01-01T00:00:00"
    mode: str = "daily"
    execution_time: float = 1.5
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    trend: str = ""


# ---------------------------------------------------------------------------
# Tests for get_trend_comparison
# ---------------------------------------------------------------------------


class TestGetTrendComparison:
    """Tests for get_trend_comparison function."""

    def test_no_history_file(self, tmp_path):
        """Returns 'No historical data' when file doesn't exist."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        result = get_trend_comparison(85.0, tmp_path)

        assert result == "No historical data"

    def test_single_entry_baseline(self, tmp_path):
        """Returns 'First baseline established' with only one entry."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        history_file = tmp_path / "history.jsonl"
        history_file.write_text(json.dumps({"overall_health_score": 80.0}) + "\n")

        result = get_trend_comparison(80.0, tmp_path)

        assert result == "First baseline established"

    def test_stable_score(self, tmp_path):
        """Returns 'Stable' when delta < 1.0."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        history_file = tmp_path / "history.jsonl"
        entries = [
            json.dumps({"overall_health_score": 85.0}),
            json.dumps({"overall_health_score": 85.5}),
        ]
        history_file.write_text("\n".join(entries) + "\n")

        result = get_trend_comparison(85.5, tmp_path)

        assert "Stable" in result

    def test_improving_score(self, tmp_path):
        """Returns 'Improving' when score increased significantly."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        history_file = tmp_path / "history.jsonl"
        entries = [
            json.dumps({"overall_health_score": 70.0}),
            json.dumps({"overall_health_score": 80.0}),
        ]
        history_file.write_text("\n".join(entries) + "\n")

        result = get_trend_comparison(80.0, tmp_path)

        assert "Improving" in result
        assert "+10.0" in result

    def test_declining_score(self, tmp_path):
        """Returns 'Declining' when score decreased significantly."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        history_file = tmp_path / "history.jsonl"
        entries = [
            json.dumps({"overall_health_score": 90.0}),
            json.dumps({"overall_health_score": 80.0}),
        ]
        history_file.write_text("\n".join(entries) + "\n")

        result = get_trend_comparison(80.0, tmp_path)

        assert "Declining" in result

    def test_invalid_json_returns_error(self, tmp_path):
        """Returns error message on corrupt history file."""
        from attune.workflows.health_check_tracking import get_trend_comparison

        history_file = tmp_path / "history.jsonl"
        history_file.write_text("not json\nnot json\n")

        result = get_trend_comparison(85.0, tmp_path)

        assert result == "Unable to determine trend"


# ---------------------------------------------------------------------------
# Tests for save_tracking_history
# ---------------------------------------------------------------------------


class TestSaveTrackingHistory:
    """Tests for save_tracking_history function."""

    def test_creates_history_file(self, tmp_path):
        """Creates history.jsonl with one entry."""
        from attune.workflows.health_check_tracking import save_tracking_history

        report = FakeHealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            category_scores=[FakeCategoryScore("Quality", 90.0)],
        )

        save_tracking_history(report, tmp_path)

        history_file = tmp_path / "history.jsonl"
        assert history_file.exists()

        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["overall_health_score"] == 85.0
        assert entry["grade"] == "B"

    def test_appends_to_existing(self, tmp_path):
        """Appends to existing history file."""
        from attune.workflows.health_check_tracking import save_tracking_history

        # Pre-populate
        history_file = tmp_path / "history.jsonl"
        history_file.write_text(json.dumps({"overall_health_score": 80.0}) + "\n")

        report = FakeHealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            category_scores=[],
        )

        save_tracking_history(report, tmp_path)

        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_category_scores_serialized(self, tmp_path):
        """Category scores are serialized as name/score dicts."""
        from attune.workflows.health_check_tracking import save_tracking_history

        report = FakeHealthCheckReport(
            overall_health_score=90.0,
            grade="A",
            category_scores=[
                FakeCategoryScore("Quality", 95.0),
                FakeCategoryScore("Security", 85.0),
            ],
        )

        save_tracking_history(report, tmp_path)

        history_file = tmp_path / "history.jsonl"
        entry = json.loads(history_file.read_text().strip())

        assert len(entry["category_scores"]) == 2
        assert entry["category_scores"][0]["name"] == "Quality"
        assert entry["category_scores"][0]["score"] == 95.0


# ---------------------------------------------------------------------------
# Tests for save_health_json
# ---------------------------------------------------------------------------


class TestSaveHealthJson:
    """Tests for save_health_json function."""

    def test_creates_health_json(self, tmp_path):
        """Creates .attune/health.json with expected structure."""
        from attune.workflows.health_check_tracking import save_health_json

        report = FakeHealthCheckReport(
            overall_health_score=85.0,
            grade="B",
            category_scores=[
                FakeCategoryScore("Quality", 8.0, raw_metrics={"quality_score": 8.0}),
                FakeCategoryScore("Security", 90.0, raw_metrics={"critical_issues": 0}),
                FakeCategoryScore("Coverage", 85.0),
            ],
        )

        save_health_json(report, tmp_path)

        health_file = tmp_path / ".attune" / "health.json"
        assert health_file.exists()

        data = json.loads(health_file.read_text())
        assert data["score"] == 85
        assert data["grade"] == "B"
        assert data["mode"] == "daily"
        assert "lint" in data
        assert "security" in data
        assert "tests" in data

    def test_security_metrics_extracted(self, tmp_path):
        """Security category metrics populate security section."""
        from attune.workflows.health_check_tracking import save_health_json

        report = FakeHealthCheckReport(
            overall_health_score=70.0,
            grade="C",
            category_scores=[
                FakeCategoryScore(
                    "Security",
                    50.0,
                    raw_metrics={"critical_issues": 2, "high_issues": 5, "medium_issues": 10},
                ),
            ],
        )

        save_health_json(report, tmp_path)

        data = json.loads((tmp_path / ".attune" / "health.json").read_text())
        assert data["security"]["high"] == 2
        assert data["security"]["medium"] == 5
        assert data["security"]["low"] == 10

    def test_coverage_above_70_populates_tests(self, tmp_path):
        """Coverage > 70% populates test metrics."""
        from attune.workflows.health_check_tracking import save_health_json

        report = FakeHealthCheckReport(
            overall_health_score=80.0,
            grade="B",
            category_scores=[FakeCategoryScore("Coverage", 85.0)],
        )

        save_health_json(report, tmp_path)

        data = json.loads((tmp_path / ".attune" / "health.json").read_text())
        assert data["tests"]["total"] == 100
        assert data["tests"]["passed"] == 85
        assert data["tests"]["coverage"] == 85

    def test_coverage_below_70_no_test_metrics(self, tmp_path):
        """Coverage <= 70% does not populate test metrics."""
        from attune.workflows.health_check_tracking import save_health_json

        report = FakeHealthCheckReport(
            overall_health_score=50.0,
            grade="D",
            category_scores=[FakeCategoryScore("Coverage", 50.0)],
        )

        save_health_json(report, tmp_path)

        data = json.loads((tmp_path / ".attune" / "health.json").read_text())
        assert data["tests"]["total"] == 0
        assert data["tests"]["passed"] == 0
