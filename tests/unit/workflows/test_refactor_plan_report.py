"""Tests for attune.workflows.refactor_plan_report.

Covers previously-uncovered branches:
- format_refactor_plan_report trajectory icons (increasing/decreasing/stable)
- _format_scan_summary with by_marker data
- _format_trajectory_analysis with velocity != 0 / positive velocity
- _format_hotspots with data
- _format_high_priority with data, > 10 items, is_hotspot flag
- _format_roadmap with real plan, truncated plan
"""

from __future__ import annotations

import pytest

from attune.workflows.refactor_plan_report import (
    _format_high_priority,
    _format_hotspots,
    _format_roadmap,
    _format_scan_summary,
    _format_trajectory_analysis,
    format_refactor_plan_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(trajectory="stable", total_debt=5, high_priority_count=2, plan="", tier="cheap"):
    return {
        "summary": {
            "total_debt": total_debt,
            "trajectory": trajectory,
            "high_priority_count": high_priority_count,
        },
        "refactoring_plan": plan,
        "model_tier_used": tier,
    }


def _input(by_marker=None, files_scanned=10, analysis=None, high_priority=None):
    return {
        "by_marker": by_marker or {},
        "files_scanned": files_scanned,
        "analysis": analysis or {},
        "high_priority": high_priority or [],
    }


# ---------------------------------------------------------------------------
# format_refactor_plan_report — trajectory icons (lines 47-55)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrajectoryIcons:
    def test_increasing_trajectory(self):
        report = format_refactor_plan_report(_result(trajectory="increasing"), _input())
        assert "INCREASING" in report

    def test_decreasing_trajectory(self):
        report = format_refactor_plan_report(_result(trajectory="decreasing"), _input())
        assert "DECREASING" in report

    def test_stable_trajectory(self):
        report = format_refactor_plan_report(_result(trajectory="stable"), _input())
        assert "STABLE" in report

    def test_unknown_trajectory_shows_stable(self):
        report = format_refactor_plan_report(_result(trajectory="unknown_val"), _input())
        assert "STABLE" in report


# ---------------------------------------------------------------------------
# _format_scan_summary — by_marker branch (lines 103-111)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatScanSummary:
    def test_no_markers_shows_files_count(self):
        lines: list[str] = []
        _format_scan_summary(lines, _input(files_scanned=42))
        combined = "\n".join(lines)
        assert "42" in combined

    def test_with_markers_shows_severity_icons(self):
        lines: list[str] = []
        _format_scan_summary(lines, _input(by_marker={"TODO": 3, "FIXME": 1, "HACK": 2}))
        combined = "\n".join(lines)
        assert "TODO" in combined
        assert "FIXME" in combined
        assert "HACK" in combined

    def test_unknown_marker_uses_grey_circle(self):
        lines: list[str] = []
        _format_scan_summary(lines, _input(by_marker={"CUSTOM_MARKER": 5}))
        combined = "\n".join(lines)
        assert "CUSTOM_MARKER" in combined


# ---------------------------------------------------------------------------
# _format_trajectory_analysis (lines 120-130)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatTrajectoryAnalysis:
    def test_empty_analysis_returns_early(self):
        lines: list[str] = []
        _format_trajectory_analysis(lines, {})
        assert lines == []

    def test_positive_velocity_shows_plus_sign(self):
        lines: list[str] = []
        _format_trajectory_analysis(lines, {"velocity": 3, "historical_snapshots": 5})
        combined = "\n".join(lines)
        assert "+3" in combined

    def test_negative_velocity_shows_minus(self):
        lines: list[str] = []
        _format_trajectory_analysis(lines, {"velocity": -2, "historical_snapshots": 4})
        combined = "\n".join(lines)
        assert "-2" in combined

    def test_zero_velocity_omits_velocity_line(self):
        lines: list[str] = []
        _format_trajectory_analysis(lines, {"velocity": 0, "historical_snapshots": 3})
        combined = "\n".join(lines)
        assert "Velocity" not in combined


# ---------------------------------------------------------------------------
# _format_hotspots (lines 138-146)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatHotspots:
    def test_empty_hotspots_returns_early(self):
        lines: list[str] = []
        _format_hotspots(lines, [])
        assert lines == []

    def test_hotspots_shown(self):
        lines: list[str] = []
        hotspots = [{"file": "src/main.py", "debt_count": 7}]
        _format_hotspots(lines, hotspots)
        combined = "\n".join(lines)
        assert "src/main.py" in combined
        assert "7" in combined

    def test_only_first_10_hotspots_shown(self):
        lines: list[str] = []
        hotspots = [{"file": f"file_{i}.py", "debt_count": i} for i in range(15)]
        _format_hotspots(lines, hotspots)
        combined = "\n".join(lines)
        assert "file_9.py" in combined
        assert "file_10.py" not in combined


# ---------------------------------------------------------------------------
# _format_high_priority (lines 149-168)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatHighPriority:
    def test_empty_returns_early(self):
        lines: list[str] = []
        _format_high_priority(lines, [])
        assert lines == []

    def test_items_shown(self):
        lines: list[str] = []
        items = [
            {
                "file": "auth.py",
                "line": 42,
                "marker": "FIXME",
                "message": "fix auth",
                "priority_score": 9,
            }
        ]
        _format_high_priority(lines, items)
        combined = "\n".join(lines)
        assert "auth.py" in combined
        assert "FIXME" in combined

    def test_is_hotspot_flag_shows_fire_icon(self):
        lines: list[str] = []
        items = [
            {
                "file": "hot.py",
                "line": 1,
                "marker": "BUG",
                "message": "bad",
                "priority_score": 10,
                "is_hotspot": True,
            }
        ]
        _format_high_priority(lines, items)
        combined = "\n".join(lines)
        assert "\U0001f525" in combined

    def test_more_than_10_shows_ellipsis(self):
        lines: list[str] = []
        items = [
            {"file": f"f{i}.py", "line": i, "marker": "TODO", "message": "msg", "priority_score": i}
            for i in range(15)
        ]
        _format_high_priority(lines, items)
        combined = "\n".join(lines)
        assert "5 more" in combined

    def test_message_truncated_at_50_chars(self):
        lines: list[str] = []
        long_msg = "A" * 100
        items = [
            {"file": "f.py", "line": 1, "marker": "TODO", "message": long_msg, "priority_score": 1}
        ]
        _format_high_priority(lines, items)
        combined = "\n".join(lines)
        # Only first 50 chars stored
        assert "A" * 51 not in combined


# ---------------------------------------------------------------------------
# _format_roadmap (lines 171-184)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatRoadmap:
    def test_empty_plan_skipped(self):
        lines: list[str] = []
        _format_roadmap(lines, {"refactoring_plan": ""})
        assert lines == []

    def test_simulated_plan_skipped(self):
        lines: list[str] = []
        _format_roadmap(lines, {"refactoring_plan": "[Simulated plan here]"})
        assert lines == []

    def test_real_plan_shown(self):
        lines: list[str] = []
        _format_roadmap(lines, {"refactoring_plan": "Step 1: Refactor auth module"})
        combined = "\n".join(lines)
        assert "Step 1" in combined

    def test_plan_over_2000_chars_truncated(self):
        lines: list[str] = []
        long_plan = "X" * 3000
        _format_roadmap(lines, {"refactoring_plan": long_plan})
        combined = "\n".join(lines)
        assert "..." in combined
        assert "X" * 2001 not in combined


# ---------------------------------------------------------------------------
# Full integration — format_refactor_plan_report
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFullReport:
    def test_full_report_with_all_sections(self):
        result = _result(
            trajectory="increasing",
            total_debt=20,
            high_priority_count=5,
            plan="Refactor now",
            tier="premium",
        )
        inp = _input(
            by_marker={"TODO": 10, "FIXME": 5, "HACK": 5},
            files_scanned=50,
            analysis={
                "velocity": 2,
                "historical_snapshots": 10,
                "hotspots": [{"file": "big.py", "debt_count": 15}],
            },
            high_priority=[
                {
                    "file": "big.py",
                    "line": 100,
                    "marker": "BUG",
                    "message": "critical",
                    "priority_score": 10,
                }
            ],
        )
        report = format_refactor_plan_report(result, inp)
        assert "REFACTOR PLAN REPORT" in report
        assert "INCREASING" in report
        assert "TODO" in report
        assert "Refactor now" in report
        assert "premium" in report
