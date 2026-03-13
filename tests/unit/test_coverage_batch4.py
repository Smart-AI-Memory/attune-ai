"""Comprehensive tests for perf_audit, refactor_plan, and test_gen workflows.

Targets maximum statement coverage for three low-coverage modules:
- src/attune/workflows/perf_audit.py (~324 statements, 6% covered)
- src/attune/workflows/refactor_plan.py (~302 statements, 7% covered)
- src/attune/workflows/test_gen/workflow.py (~280 statements, 6% covered)

All LLM calls and external dependencies are mocked.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
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
# RefactorPlanWorkflow Tests
# ============================================================================


@pytest.mark.unit
class TestRefactorPlanConstants:
    """Tests for refactor plan constants."""

    def test_refactor_plan_steps_has_plan(self) -> None:
        """Verify REFACTOR_PLAN_STEPS has plan configuration."""
        assert "plan" in REFACTOR_PLAN_STEPS
        step = REFACTOR_PLAN_STEPS["plan"]
        assert step.name == "plan"
        assert step.tier_hint == "premium"
        assert step.max_tokens == 3000

    def test_debt_markers_keys(self) -> None:
        """Verify DEBT_MARKERS has expected markers."""
        expected = {"TODO", "FIXME", "HACK", "XXX", "BUG", "OPTIMIZE", "REFACTOR"}
        assert set(DEBT_MARKERS.keys()) == expected

    def test_debt_markers_have_required_fields(self) -> None:
        """Verify each marker has severity and weight."""
        for marker, info in DEBT_MARKERS.items():
            assert "severity" in info, f"{marker} missing severity"
            assert "weight" in info, f"{marker} missing weight"
            assert info["severity"] in {"high", "medium", "low"}


@pytest.mark.unit
class TestRefactorPlanWorkflowInit:
    """Tests for RefactorPlanWorkflow initialization."""

    def test_default_initialization(self, cost_tracker: Any) -> None:
        """Test default workflow initialization."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        assert wf.name == "refactor-plan"
        assert wf.min_debt_for_premium == 50
        assert wf._total_debt == 0
        assert wf._debt_history == []
        assert wf.use_crew_for_analysis is True

    def test_custom_initialization(self, cost_tracker: Any) -> None:
        """Test workflow with custom parameters."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_debt_for_premium=100,
            use_crew_for_analysis=False,
            crew_config={"timeout": 30},
        )
        assert wf.min_debt_for_premium == 100
        assert wf.use_crew_for_analysis is False
        assert wf.crew_config == {"timeout": 30}

    def test_stages_and_tier_map(self, cost_tracker: Any) -> None:
        """Verify stages and tier mappings."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        assert wf.stages == ["scan", "analyze", "prioritize", "plan"]
        assert wf.tier_map["scan"] == ModelTier.CHEAP
        assert wf.tier_map["analyze"] == ModelTier.CAPABLE
        assert wf.tier_map["prioritize"] == ModelTier.CAPABLE
        assert wf.tier_map["plan"] == ModelTier.PREMIUM

    def test_load_debt_history_from_file(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test loading debt history from tech_debt.json."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debt_file = patterns_dir / "tech_debt.json"
        debt_file.write_text(
            json.dumps(
                {
                    "snapshots": [
                        {"total_items": 10, "date": "2025-01-01"},
                        {"total_items": 15, "date": "2025-02-01"},
                    ],
                },
            ),
        )
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir=str(patterns_dir),
        )
        assert len(wf._debt_history) == 2

    def test_load_debt_history_missing_file(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test missing debt history file is handled gracefully."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir=str(tmp_path),
        )
        assert wf._debt_history == []

    def test_load_debt_history_invalid_json(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test invalid JSON in debt history is handled gracefully."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debt_file = patterns_dir / "tech_debt.json"
        debt_file.write_text("not json at all{{{")
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir=str(patterns_dir),
        )
        assert wf._debt_history == []


@pytest.mark.unit
class TestRefactorPlanShouldSkipStage:
    """Tests for conditional stage skipping."""

    def test_plan_downgrade_low_debt(self, cost_tracker: Any) -> None:
        """Test plan downgrades to CAPABLE with low debt."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_debt_for_premium=50,
        )
        wf._total_debt = 10
        should_skip, reason = wf.should_skip_stage("plan", {})
        assert should_skip is False
        assert reason is None
        assert wf.tier_map["plan"] == ModelTier.CAPABLE

    def test_plan_stays_premium_high_debt(self, cost_tracker: Any) -> None:
        """Test plan stays PREMIUM with enough debt."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_debt_for_premium=50,
        )
        # Explicitly reset tier_map (class-level dict may be mutated by prior tests)
        wf.tier_map["plan"] = ModelTier.PREMIUM
        wf._total_debt = 100
        should_skip, reason = wf.should_skip_stage("plan", {})
        assert should_skip is False
        assert reason is None
        assert wf.tier_map["plan"] == ModelTier.PREMIUM

    def test_non_plan_stage_not_skipped(self, cost_tracker: Any) -> None:
        """Test non-plan stages are never skipped."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        for stage in ["scan", "analyze", "prioritize"]:
            should_skip, reason = wf.should_skip_stage(stage, {})
            assert should_skip is False


@pytest.mark.unit
class TestRefactorPlanRunStage:
    """Tests for run_stage dispatch."""

    @pytest.mark.asyncio
    async def test_run_stage_unknown_raises(self, cost_tracker: Any) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        with pytest.raises(ValueError, match="Unknown stage: bogus"):
            await wf.run_stage("bogus", ModelTier.CHEAP, {})

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_to_all_stages(self, cost_tracker: Any) -> None:
        """Test run_stage dispatches to all four stages."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        for stage_name, method_name in [
            ("scan", "_scan"),
            ("analyze", "_analyze"),
            ("prioritize", "_prioritize"),
            ("plan", "_plan"),
        ]:
            with patch.object(wf, method_name, new_callable=AsyncMock) as mock:
                mock.return_value = ({}, 1, 1)
                await wf.run_stage(stage_name, ModelTier.CHEAP, {})
                mock.assert_awaited_once()


@pytest.mark.unit
class TestRefactorPlanScan:
    """Tests for the _scan stage."""

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test scanning empty directory."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_debt"] == 0
        assert result["debt_items"] == []
        assert result["files_scanned"] == 0

    @pytest.mark.asyncio
    async def test_scan_detects_todo_fixme_hack(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test scanning detects TODO, FIXME, HACK markers."""
        sub = tmp_path / "src"
        sub.mkdir()
        code = """# TODO: fix this later
# FIXME: broken logic
# HACK: temporary workaround
# BUG: known issue
x = 1
"""
        py_file = sub / "code.py"
        py_file.write_text(code)

        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_debt"] == 4
        assert result["files_scanned"] == 1
        markers_found = {item["marker"] for item in result["debt_items"]}
        assert "TODO" in markers_found
        assert "FIXME" in markers_found
        assert "HACK" in markers_found
        assert "BUG" in markers_found

    @pytest.mark.asyncio
    async def test_scan_by_file_and_marker_grouping(
        self,
        cost_tracker: Any,
        tmp_path: Path,
    ) -> None:
        """Test scan groups debt items by file and by marker type."""
        sub = tmp_path / "src"
        sub.mkdir()
        file_a = sub / "a.py"
        file_a.write_text("# TODO: item1\n# TODO: item2\n")
        file_b = sub / "b.py"
        file_b.write_text("# FIXME: item3\n")

        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_debt"] == 3
        by_file = result["by_file"]
        assert len(by_file) == 2
        by_marker = result["by_marker"]
        assert by_marker.get("TODO", 0) == 2
        assert by_marker.get("FIXME", 0) == 1

    @pytest.mark.asyncio
    async def test_scan_skips_excluded_dirs(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test scan skips venv, node_modules, etc."""
        venv_dir = tmp_path / "src" / "venv"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "lib.py"
        venv_file.write_text("# TODO: should be skipped\n")

        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_debt"] == 0

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self, cost_tracker: Any) -> None:
        """Test scanning nonexistent path returns empty results."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._scan(
            {"path": "/nonexistent/xyz", "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_debt"] == 0

    @pytest.mark.asyncio
    async def test_scan_updates_total_debt(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test scan updates self._total_debt."""
        sub = tmp_path / "src"
        sub.mkdir()
        py_file = sub / "a.py"
        py_file.write_text("# TODO: item\n# FIXME: item2\n")

        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        await wf._scan({"path": str(tmp_path), "file_types": [".py"]}, ModelTier.CHEAP)
        assert wf._total_debt == 2


@pytest.mark.unit
class TestRefactorPlanAnalyze:
    """Tests for the _analyze stage."""

    @pytest.mark.asyncio
    async def test_analyze_trajectory_stable(self, cost_tracker: Any) -> None:
        """Test trajectory is stable with no history."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._analyze(
            {"total_debt": 10, "by_file": {"a.py": 5}},
            ModelTier.CAPABLE,
        )
        analysis = result["analysis"]
        assert analysis["trajectory"] == "stable"
        assert analysis["velocity"] == 0.0

    @pytest.mark.asyncio
    async def test_analyze_trajectory_increasing(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test trajectory is increasing with growing debt history."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debt_file = patterns_dir / "tech_debt.json"
        debt_file.write_text(json.dumps({"snapshots": [{"total_items": 10}, {"total_items": 30}]}))
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir=str(patterns_dir))
        result, _, _ = await wf._analyze(
            {"total_debt": 30, "by_file": {"a.py": 10}},
            ModelTier.CAPABLE,
        )
        assert result["analysis"]["trajectory"] == "increasing"
        assert result["analysis"]["velocity"] > 0

    @pytest.mark.asyncio
    async def test_analyze_trajectory_decreasing(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test trajectory is decreasing with shrinking debt history."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debt_file = patterns_dir / "tech_debt.json"
        debt_file.write_text(json.dumps({"snapshots": [{"total_items": 50}, {"total_items": 20}]}))
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir=str(patterns_dir))
        result, _, _ = await wf._analyze({"total_debt": 20, "by_file": {}}, ModelTier.CAPABLE)
        assert result["analysis"]["trajectory"] == "decreasing"

    @pytest.mark.asyncio
    async def test_analyze_hotspots(self, cost_tracker: Any) -> None:
        """Test analyze identifies hotspot files."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        result, _, _ = await wf._analyze(
            {"total_debt": 20, "by_file": {"a.py": 10, "b.py": 5, "c.py": 3}},
            ModelTier.CAPABLE,
        )
        hotspots = result["analysis"]["hotspots"]
        assert len(hotspots) == 3
        assert hotspots[0]["file"] == "a.py"


@pytest.mark.unit
class TestRefactorPlanPrioritize:
    """Tests for the _prioritize stage."""

    @pytest.mark.asyncio
    async def test_prioritize_empty_items(self, cost_tracker: Any) -> None:
        """Test prioritizing with no debt items."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            use_crew_for_analysis=False,
        )
        wf._crew_available = False

        result, _, _ = await wf._prioritize(
            {"debt_items": [], "analysis": {"hotspots": []}},
            ModelTier.CAPABLE,
        )
        assert result["prioritized_items"] == []
        assert result["high_priority"] == []
        assert result["low_priority_count"] == 0

    @pytest.mark.asyncio
    async def test_prioritize_scores_correctly(self, cost_tracker: Any) -> None:
        """Test priority scoring logic."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            use_crew_for_analysis=False,
        )
        debt_items = [
            {"file": "hot.py", "marker": "HACK", "severity": "high", "weight": 5},
            {"file": "cold.py", "marker": "TODO", "severity": "low", "weight": 1},
        ]
        analysis = {"hotspots": [{"file": "hot.py"}]}

        result, _, _ = await wf._prioritize(
            {"debt_items": debt_items, "analysis": analysis},
            ModelTier.CAPABLE,
        )
        items = result["prioritized_items"]
        # hot.py: base=5, severity_factor=3 (high), hotspot_bonus=2 => 5*3+2=17
        assert items[0]["file"] == "hot.py"
        assert items[0]["priority_score"] == 17
        assert items[0]["is_hotspot"] is True

        # cold.py: base=1, severity_factor=1 (low), hotspot_bonus=0 => 1*1+0=1
        assert items[1]["file"] == "cold.py"
        assert items[1]["priority_score"] == 1
        assert items[1]["is_hotspot"] is False

    @pytest.mark.asyncio
    async def test_prioritize_groups_into_tiers(self, cost_tracker: Any) -> None:
        """Test prioritize groups items into high/medium/low."""
        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            use_crew_for_analysis=False,
        )
        debt_items = [
            {"file": "a.py", "marker": "HACK", "severity": "high", "weight": 5},  # 5*3=15 (high)
            {
                "file": "b.py",
                "marker": "FIXME",
                "severity": "medium",
                "weight": 3,
            },  # 3*2=6 (medium)
            {"file": "c.py", "marker": "TODO", "severity": "low", "weight": 1},  # 1*1=1 (low)
        ]
        result, _, _ = await wf._prioritize(
            {"debt_items": debt_items, "analysis": {"hotspots": []}},
            ModelTier.CAPABLE,
        )
        assert len(result["high_priority"]) == 1
        assert len(result["medium_priority"]) == 1
        assert result["low_priority_count"] == 1

    @pytest.mark.asyncio
    async def test_prioritize_with_crew_available(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test prioritize with crew analysis enabled."""
        code_file = tmp_path / "hot.py"
        code_file.write_text("x = 1\n")

        wf = RefactorPlanWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            use_crew_for_analysis=True,
        )

        mock_finding = MagicMock()
        mock_finding.file_path = str(code_file)
        mock_finding.start_line = 1
        mock_finding.title = "Refactor opportunity"
        mock_finding.description = "Can improve"
        mock_finding.severity = MagicMock(value="high")
        mock_finding.category = MagicMock(value="complexity")

        mock_crew_result = MagicMock()
        mock_crew_result.findings = [mock_finding]

        mock_crew = AsyncMock()
        mock_crew.analyze = AsyncMock(return_value=mock_crew_result)

        wf._crew = mock_crew
        wf._crew_available = True

        debt_items = [
            {"file": str(code_file), "marker": "HACK", "severity": "high", "weight": 5},
        ]
        analysis = {"hotspots": [{"file": str(code_file)}]}

        result, _, _ = await wf._prioritize(
            {"debt_items": debt_items, "analysis": analysis},
            ModelTier.CAPABLE,
        )
        assert result["crew_enhanced"] is True
        assert result["crew_findings_count"] >= 1


@pytest.mark.unit
class TestRefactorPlanPlan:
    """Tests for the _plan stage (LLM call)."""

    @pytest.mark.asyncio
    async def test_plan_legacy_path(self, cost_tracker: Any) -> None:
        """Test plan uses legacy _call_llm path."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        wf._executor = None
        wf._api_key = None

        input_data = {
            "high_priority": [
                {"file": "a.py", "line": 10, "marker": "HACK", "message": "temp fix"},
            ],
            "medium_priority": [],
            "analysis": {"trajectory": "stable", "velocity": 0, "hotspots": []},
            "total_debt": 5,
            "target": "my-project",
        }

        with (
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("Phase 1: Fix hacks...", 100, 200),
            ),
            patch.object(wf, "_parse_xml_response", return_value={}),
            patch.object(wf, "_is_xml_enabled", return_value=False),
        ):
            result, in_tokens, out_tokens = await wf._plan(input_data, ModelTier.PREMIUM)

        assert result["refactoring_plan"] == "Phase 1: Fix hacks..."
        assert result["summary"]["total_debt"] == 5
        assert result["summary"]["trajectory"] == "stable"
        assert result["model_tier_used"] == "premium"
        assert "formatted_report" in result

    @pytest.mark.asyncio
    async def test_plan_with_xml_enabled(self, cost_tracker: Any) -> None:
        """Test plan uses XML-enhanced prompts."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        wf._executor = None
        wf._api_key = None

        input_data = {
            "high_priority": [],
            "medium_priority": [],
            "analysis": {"trajectory": "stable", "velocity": 0, "hotspots": []},
            "total_debt": 0,
        }

        with (
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("XML plan", 50, 100),
            ),
            patch.object(
                wf,
                "_parse_xml_response",
                return_value={
                    "xml_parsed": True,
                    "summary": "Clean codebase",
                    "findings": [],
                    "checklist": ["Review done"],
                },
            ),
            patch.object(wf, "_is_xml_enabled", return_value=True),
            patch.object(wf, "_render_xml_prompt", return_value="<xml>prompt</xml>"),
        ):
            result, _, _ = await wf._plan(input_data, ModelTier.CAPABLE)

        assert result["xml_parsed"] is True
        assert result["plan_summary"] == "Clean codebase"

    @pytest.mark.asyncio
    async def test_plan_executor_fallback(self, cost_tracker: Any) -> None:
        """Test plan falls back to _call_llm when executor fails."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        wf._executor = MagicMock()
        wf._api_key = "test-key"

        input_data = {
            "high_priority": [],
            "medium_priority": [],
            "analysis": {"trajectory": "stable", "velocity": 0, "hotspots": []},
            "total_debt": 0,
        }

        with (
            patch.object(
                wf,
                "run_step_with_executor",
                new_callable=AsyncMock,
                side_effect=RuntimeError("executor error"),
            ),
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("Fallback plan", 30, 60),
            ),
            patch.object(wf, "_parse_xml_response", return_value={}),
            patch.object(wf, "_is_xml_enabled", return_value=False),
        ):
            result, _, _ = await wf._plan(input_data, ModelTier.PREMIUM)

        assert result["refactoring_plan"] == "Fallback plan"


@pytest.mark.unit
class TestRefactorPlanFormatReport:
    """Tests for format_refactor_plan_report function."""

    def test_format_increasing_trajectory(self) -> None:
        """Test formatting with increasing trajectory."""
        result = {
            "summary": {"total_debt": 50, "trajectory": "increasing", "high_priority_count": 10},
            "refactoring_plan": "Phase 1: ...",
            "model_tier_used": "premium",
        }
        input_data = {
            "by_marker": {"TODO": 20, "FIXME": 15, "HACK": 10, "BUG": 5},
            "files_scanned": 100,
            "analysis": {
                "velocity": 5.0,
                "historical_snapshots": 3,
                "hotspots": [{"file": "a.py", "debt_count": 10}],
            },
            "high_priority": [
                {
                    "file": "a.py",
                    "line": 5,
                    "marker": "HACK",
                    "message": "temp fix",
                    "priority_score": 15,
                    "is_hotspot": True,
                },
            ],
        }
        report = format_refactor_plan_report(result, input_data)
        assert "REFACTOR PLAN REPORT" in report
        assert "INCREASING" in report
        assert "Total Tech Debt Items: 50" in report
        assert "TRAJECTORY ANALYSIS" in report
        assert "HOTSPOT FILES" in report
        assert "HIGH PRIORITY ITEMS" in report
        assert "REFACTORING ROADMAP" in report

    def test_format_decreasing_trajectory(self) -> None:
        """Test formatting with decreasing trajectory."""
        result = {
            "summary": {"total_debt": 10, "trajectory": "decreasing", "high_priority_count": 0},
            "refactoring_plan": "",
            "model_tier_used": "capable",
        }
        input_data = {
            "by_marker": {},
            "files_scanned": 50,
            "analysis": {"velocity": -3.0, "historical_snapshots": 2, "hotspots": []},
            "high_priority": [],
        }
        report = format_refactor_plan_report(result, input_data)
        assert "DECREASING" in report

    def test_format_stable_trajectory(self) -> None:
        """Test formatting with stable trajectory."""
        result = {
            "summary": {"total_debt": 20, "trajectory": "stable", "high_priority_count": 0},
            "refactoring_plan": "",
            "model_tier_used": "capable",
        }
        input_data = {
            "by_marker": {},
            "files_scanned": 0,
            "analysis": {"velocity": 0, "historical_snapshots": 0, "hotspots": []},
            "high_priority": [],
        }
        report = format_refactor_plan_report(result, input_data)
        assert "STABLE" in report

    def test_format_long_plan_truncated(self) -> None:
        """Test formatting truncates very long refactoring plans."""
        result = {
            "summary": {"total_debt": 10, "trajectory": "stable", "high_priority_count": 0},
            "refactoring_plan": "A" * 3000,
            "model_tier_used": "premium",
        }
        input_data = {
            "by_marker": {},
            "files_scanned": 0,
            "analysis": {"velocity": 0, "historical_snapshots": 0, "hotspots": []},
            "high_priority": [],
        }
        report = format_refactor_plan_report(result, input_data)
        assert "..." in report

    def test_format_simulated_plan_excluded(self) -> None:
        """Test formatting excludes simulated plans."""
        result = {
            "summary": {"total_debt": 10, "trajectory": "stable", "high_priority_count": 0},
            "refactoring_plan": "[Simulated response]",
            "model_tier_used": "premium",
        }
        input_data = {
            "by_marker": {},
            "files_scanned": 0,
            "analysis": {"velocity": 0, "historical_snapshots": 0, "hotspots": []},
            "high_priority": [],
        }
        report = format_refactor_plan_report(result, input_data)
        assert "REFACTORING ROADMAP" not in report

    def test_format_many_high_priority_shows_overflow(self) -> None:
        """Test formatting shows overflow count for many high priority items."""
        result = {
            "summary": {"total_debt": 50, "trajectory": "stable", "high_priority_count": 15},
            "refactoring_plan": "",
            "model_tier_used": "premium",
        }
        high_items = [
            {
                "file": f"file_{i}.py",
                "line": i,
                "marker": "HACK",
                "message": f"issue {i}",
                "priority_score": 15,
                "is_hotspot": False,
            }
            for i in range(15)
        ]
        input_data = {
            "by_marker": {"HACK": 15},
            "files_scanned": 50,
            "analysis": {"velocity": 0, "historical_snapshots": 0, "hotspots": []},
            "high_priority": high_items,
        }
        report = format_refactor_plan_report(result, input_data)
        assert "... and 5 more" in report


@pytest.mark.unit
class TestRefactorPlanInitializeCrew:
    """Tests for _initialize_crew method."""

    @pytest.mark.asyncio
    async def test_crew_already_initialized(self, cost_tracker: Any) -> None:
        """Test crew initialization skips if already initialized."""
        wf = RefactorPlanWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        existing_crew = MagicMock()
        wf._crew = existing_crew

        await wf._initialize_crew()
        # Should not change the existing crew
        assert wf._crew is existing_crew
