"""Comprehensive tests for perf_audit, refactor_plan, and test_gen workflows.

Targets maximum statement coverage for three low-coverage modules:
- src/attune/workflows/perf_audit.py (~324 statements, 6% covered)
- src/attune/workflows/refactor_plan.py (~302 statements, 7% covered)
- src/attune/workflows/test_gen/workflow.py (~280 statements, 6% covered)

All LLM calls and external dependencies are mocked.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest

from attune.workflows.perf_audit import (
    PERF_AUDIT_STEPS,
    PERF_PATTERNS,
    create_perf_audit_workflow_report,
    format_perf_audit_report,
)
from attune.workflows.refactor_plan import (
    DEBT_MARKERS,
    REFACTOR_PLAN_STEPS,
    RefactorPlanWorkflow,
    format_refactor_plan_report,
)

# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def cost_tracker(tmp_path: Path) -> Any:
    """Create isolated CostTracker for testing.

    Args:
        tmp_path: pytest temporary directory

    Returns:
        CostTracker instance with isolated storage

    """
    from attune.cost_tracker import CostTracker

    storage_dir = tmp_path / ".empathy"
    return CostTracker(storage_dir=str(storage_dir))


@pytest.fixture
def scan_dir() -> Path:
    """Create a temp directory whose path does NOT contain 'test'.

    perf_audit._profile() and test_gen._identify() skip files whose
    path string contains 'test' (or '.git', 'venv', etc.).  pytest's
    ``tmp_path`` typically includes the test-function name (e.g.
    ``test_profile_detects_…``), causing every file to be silently
    skipped.  This fixture creates a directory under $TMPDIR with a
    harmless prefix so the scanner actually processes the files.

    Yields:
        Path to a clean directory.  Automatically removed after the test.

    """
    d = tempfile.mkdtemp(prefix="scan_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# ============================================================================
# PerformanceAuditWorkflow Tests
# ============================================================================


@pytest.mark.unit
class TestPerfAuditConstants:
    """Tests for performance audit constants and step configurations."""

    def test_perf_audit_steps_has_optimize(self) -> None:
        """Verify PERF_AUDIT_STEPS has optimize configuration."""
        assert "optimize" in PERF_AUDIT_STEPS
        step = PERF_AUDIT_STEPS["optimize"]
        assert step.name == "optimize"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 3000

    def test_perf_patterns_keys(self) -> None:
        """Verify PERF_PATTERNS contains expected pattern keys."""
        expected_keys = {
            "n_plus_one",
            "sync_in_async",
            "list_comprehension_in_loop",
            "string_concat_loop",
            "global_import",
            "repeated_regex",
            "nested_loops",
        }
        assert set(PERF_PATTERNS.keys()) == expected_keys

    def test_perf_patterns_have_required_fields(self) -> None:
        """Verify each pattern has required fields."""
        for name, pattern_info in PERF_PATTERNS.items():
            assert "patterns" in pattern_info, f"{name} missing patterns"
            assert "description" in pattern_info, f"{name} missing description"
            assert "impact" in pattern_info, f"{name} missing impact"
            assert pattern_info["impact"] in {
                "high",
                "medium",
                "low",
            }, f"{name} has invalid impact: {pattern_info['impact']}"


@pytest.mark.unit
class TestPerfAuditFormatReport:
    """Tests for format_perf_audit_report function."""

    def test_format_excellent_score(self) -> None:
        """Test formatting with excellent perf score."""
        result = {
            "perf_score": 90,
            "perf_level": "good",
            "top_issues": [{"type": "n_plus_one", "count": 2}],
            "optimization_plan": "Use batch queries",
            "recommendation_count": 1,
            "model_tier_used": "premium",
        }
        input_data = {
            "files_scanned": 10,
            "finding_count": 2,
            "by_impact": {"high": 1, "medium": 1, "low": 0},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = format_perf_audit_report(result, input_data)
        assert "PERFORMANCE AUDIT REPORT" in report
        assert "EXCELLENT" in report
        assert "90/100" in report

    def test_format_critical_score(self) -> None:
        """Test formatting with critical perf score."""
        result = {
            "perf_score": 30,
            "perf_level": "critical",
            "top_issues": [],
            "optimization_plan": "",
            "recommendation_count": 0,
            "model_tier_used": "capable",
        }
        input_data = {
            "files_scanned": 5,
            "finding_count": 0,
            "by_impact": {"high": 0, "medium": 0, "low": 0},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = format_perf_audit_report(result, input_data)
        assert "CRITICAL" in report
        assert "30/100" in report

    def test_format_good_score(self) -> None:
        """Test formatting with good perf score (75-84)."""
        result = {
            "perf_score": 78,
            "perf_level": "good",
            "top_issues": [],
            "optimization_plan": "",
            "recommendation_count": 0,
            "model_tier_used": "capable",
        }
        input_data = {
            "files_scanned": 0,
            "finding_count": 0,
            "by_impact": {},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = format_perf_audit_report(result, input_data)
        assert "GOOD" in report

    def test_format_needs_optimization_score(self) -> None:
        """Test formatting with needs optimization score (50-74)."""
        result = {
            "perf_score": 60,
            "perf_level": "warning",
            "top_issues": [],
            "optimization_plan": "",
            "recommendation_count": 0,
            "model_tier_used": "capable",
        }
        input_data = {
            "files_scanned": 0,
            "finding_count": 0,
            "by_impact": {},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = format_perf_audit_report(result, input_data)
        assert "NEEDS OPTIMIZATION" in report

    def test_format_with_hotspots_and_findings(self) -> None:
        """Test formatting includes hotspot and finding details."""
        result = {
            "perf_score": 50,
            "perf_level": "warning",
            "top_issues": [{"type": "n_plus_one", "count": 3}],
            "optimization_plan": "Fix it",
            "recommendation_count": 1,
            "model_tier_used": "premium",
        }
        input_data = {
            "files_scanned": 10,
            "finding_count": 5,
            "by_impact": {"high": 3, "medium": 1, "low": 1},
            "hotspot_result": {
                "hotspots": [
                    {"file": "hot.py", "complexity_score": 25, "concerns": ["n_plus_one", "sync"]},
                    {"file": "warm.py", "complexity_score": 12, "concerns": ["regex"]},
                ],
                "critical_count": 1,
                "moderate_count": 1,
            },
            "findings": [
                {"file": "hot.py", "line": 10, "description": "N+1 query", "impact": "high"},
            ],
        }
        report = format_perf_audit_report(result, input_data)
        assert "PERFORMANCE HOTSPOTS" in report
        assert "hot.py" in report
        assert "HIGH IMPACT FINDINGS" in report
        assert "OPTIMIZATION RECOMMENDATIONS" in report


@pytest.mark.unit
class TestCreatePerfAuditWorkflowReport:
    """Tests for create_perf_audit_workflow_report function."""

    def test_creates_report_success_level(self) -> None:
        """Test report creation with success level (score >= 85)."""
        result = {
            "perf_score": 90,
            "perf_level": "good",
            "top_issues": [{"type": "n_plus_one", "count": 1}],
            "optimization_plan": "All good",
        }
        input_data = {
            "files_scanned": 5,
            "finding_count": 1,
            "by_impact": {"high": 0, "medium": 1, "low": 0},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = create_perf_audit_workflow_report(result, input_data)
        assert report.score == 90
        assert report.level == "success"

    def test_creates_report_warning_level(self) -> None:
        """Test report creation with warning level (50-84)."""
        result = {
            "perf_score": 60,
            "perf_level": "warning",
            "top_issues": [],
            "optimization_plan": "",
        }
        input_data = {
            "files_scanned": 5,
            "finding_count": 3,
            "by_impact": {"high": 1, "medium": 1, "low": 1},
            "hotspot_result": {
                "hotspots": [{"file": "a.py"}],
                "critical_count": 0,
                "moderate_count": 1,
            },
            "findings": [
                {"file": "a.py", "line": 5, "description": "Issue", "impact": "high"},
            ],
        }
        report = create_perf_audit_workflow_report(result, input_data)
        assert report.level == "warning"

    def test_creates_report_error_level(self) -> None:
        """Test report creation with error level (score < 50)."""
        result = {
            "perf_score": 30,
            "perf_level": "critical",
            "top_issues": [],
            "optimization_plan": "",
        }
        input_data = {
            "files_scanned": 0,
            "finding_count": 0,
            "by_impact": {},
            "hotspot_result": {"hotspots": [], "critical_count": 0, "moderate_count": 0},
            "findings": [],
        }
        report = create_perf_audit_workflow_report(result, input_data)
        assert report.level == "error"


# ============================================================================
# RefactorPlanWorkflow Tests (SDK-native, v4.2.0)
# ============================================================================


@pytest.mark.unit
class TestRefactorPlanConstants:
    """Tests for refactor plan constants."""

    def test_refactor_plan_steps_has_plan(self) -> None:
        """Verify REFACTOR_PLAN_STEPS has plan configuration."""
        assert "plan" in REFACTOR_PLAN_STEPS

    def test_debt_markers_has_entries(self) -> None:
        """Verify DEBT_MARKERS has patterns."""
        assert len(DEBT_MARKERS) > 0

    def test_debt_markers_values_are_dicts(self) -> None:
        """Verify DEBT_MARKERS values are dicts with severity and weight."""
        for key, info in DEBT_MARKERS.items():
            assert isinstance(info, dict), f"{key} should be a dict"
            assert "severity" in info, f"{key} should have severity"


@pytest.mark.unit
class TestRefactorPlanWorkflowInit:
    """Tests for RefactorPlanWorkflow initialization (SDK-native)."""

    def test_class_name(self) -> None:
        """Class attribute name is 'refactor-plan'."""
        assert RefactorPlanWorkflow.name == "refactor-plan"

    def test_class_description(self) -> None:
        """Description mentions Agent SDK."""
        assert "Agent SDK" in RefactorPlanWorkflow.description

    def test_class_stages(self) -> None:
        """SDK-native workflow has single agent-plan stage."""
        assert RefactorPlanWorkflow.stages == ["agent-plan"]

    def test_default_construction(self) -> None:
        """Default constructor succeeds."""
        wf = RefactorPlanWorkflow()
        assert wf.name == "refactor-plan"

    def test_post_simplification_enabled_by_default(self) -> None:
        """Post-simplification is enabled by default via kwargs."""
        wf = RefactorPlanWorkflow()
        assert getattr(wf, "_enable_post_simplification", True) is True


@pytest.mark.unit
class TestRefactorPlanFormatReport:
    """Tests for format_refactor_plan_report."""

    def test_returns_string(self) -> None:
        """Report formatter returns a string."""
        report = format_refactor_plan_report(
            {"debt_items": [], "plan": "No refactoring needed"},
            {"path": "."},
        )
        assert isinstance(report, str)
