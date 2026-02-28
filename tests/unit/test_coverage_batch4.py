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
    PerformanceAuditWorkflow,
    create_perf_audit_workflow_report,
    format_perf_audit_report,
)
from attune.workflows.refactor_plan import (
    DEBT_MARKERS,
    REFACTOR_PLAN_STEPS,
    RefactorPlanWorkflow,
    format_refactor_plan_report,
)
from attune.workflows.test_gen.workflow import TestGenerationWorkflow

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
class TestPerfAuditWorkflowInit:
    """Tests for PerformanceAuditWorkflow initialization."""

    def test_default_initialization(self, cost_tracker: Any) -> None:
        """Test workflow initializes with default settings."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker)
        assert wf.name == "perf-audit"
        assert wf.min_hotspots_for_premium == 3
        assert wf.enable_auth_strategy is True
        assert wf._hotspot_count == 0
        assert wf._auth_mode_used is None

    def test_custom_initialization(self, cost_tracker: Any) -> None:
        """Test workflow with custom parameters."""
        wf = PerformanceAuditWorkflow(
            cost_tracker=cost_tracker,
            min_hotspots_for_premium=5,
            enable_auth_strategy=False,
        )
        assert wf.min_hotspots_for_premium == 5
        assert wf.enable_auth_strategy is False

    def test_stages_and_tier_map(self, cost_tracker: Any) -> None:
        """Verify stages and tier mappings."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker)
        assert wf.stages == ["profile", "analyze", "hotspots", "optimize"]
        assert wf.tier_map["profile"] == ModelTier.CHEAP
        assert wf.tier_map["analyze"] == ModelTier.CAPABLE
        assert wf.tier_map["hotspots"] == ModelTier.CAPABLE
        assert wf.tier_map["optimize"] == ModelTier.PREMIUM


@pytest.mark.unit
class TestPerfAuditShouldSkipStage:
    """Tests for conditional stage skipping logic."""

    def test_optimize_downgrade_few_hotspots(self, cost_tracker: Any) -> None:
        """Test optimize stage downgrades to CAPABLE with few hotspots."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, min_hotspots_for_premium=3)
        wf._hotspot_count = 2
        should_skip, reason = wf.should_skip_stage("optimize", {})
        assert should_skip is False
        assert reason is None
        assert wf.tier_map["optimize"] == ModelTier.CAPABLE

    def test_optimize_stays_premium_many_hotspots(self, cost_tracker: Any) -> None:
        """Test optimize stays PREMIUM with enough hotspots.

        Note: tier_map is a class-level dict, so prior tests may have mutated it.
        We explicitly set it back to PREMIUM to test the 'enough hotspots' path.
        """
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, min_hotspots_for_premium=3)
        # Reset to PREMIUM since class-level dict may have been mutated
        wf.tier_map["optimize"] = ModelTier.PREMIUM
        wf._hotspot_count = 5
        should_skip, reason = wf.should_skip_stage("optimize", {})
        assert should_skip is False
        assert reason is None
        # With hotspot_count >= min_hotspots_for_premium, the method returns early
        # without changing tier_map, so it stays PREMIUM
        assert wf.tier_map["optimize"] == ModelTier.PREMIUM

    def test_non_optimize_stage_never_skipped(self, cost_tracker: Any) -> None:
        """Test non-optimize stages are never skipped."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker)
        for stage in ["profile", "analyze", "hotspots"]:
            should_skip, reason = wf.should_skip_stage(stage, {})
            assert should_skip is False
            assert reason is None


@pytest.mark.unit
class TestPerfAuditRunStage:
    """Tests for run_stage dispatch."""

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_to_profile(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _profile."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        with patch.object(wf, "_profile", new_callable=AsyncMock) as mock_profile:
            mock_profile.return_value = ({"result": "profile"}, 10, 20)
            result = await wf.run_stage("profile", ModelTier.CHEAP, {"path": "."})
            mock_profile.assert_awaited_once_with({"path": "."}, ModelTier.CHEAP)
            assert result == ({"result": "profile"}, 10, 20)

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_to_analyze(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _analyze."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        with patch.object(wf, "_analyze", new_callable=AsyncMock) as mock:
            mock.return_value = ({"result": "analyze"}, 10, 20)
            result = await wf.run_stage("analyze", ModelTier.CAPABLE, {})
            mock.assert_awaited_once()
            assert result[0]["result"] == "analyze"

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_to_hotspots(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _hotspots."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        with patch.object(wf, "_hotspots", new_callable=AsyncMock) as mock:
            mock.return_value = ({"result": "hotspots"}, 10, 20)
            result = await wf.run_stage("hotspots", ModelTier.CAPABLE, {})
            mock.assert_awaited_once()
            assert result[0]["result"] == "hotspots"

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_to_optimize(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _optimize."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        with patch.object(wf, "_optimize", new_callable=AsyncMock) as mock:
            mock.return_value = ({"result": "optimize"}, 10, 20)
            result = await wf.run_stage("optimize", ModelTier.PREMIUM, {})
            mock.assert_awaited_once()
            assert result[0]["result"] == "optimize"

    @pytest.mark.asyncio
    async def test_run_stage_unknown_raises_value_error(self, cost_tracker: Any) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        with pytest.raises(ValueError, match="Unknown stage: nonexistent"):
            await wf.run_stage("nonexistent", ModelTier.CHEAP, {})


@pytest.mark.unit
class TestPerfAuditProfile:
    """Tests for the _profile stage (static analysis)."""

    @pytest.mark.asyncio
    async def test_profile_empty_directory(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test profiling an empty directory returns no findings."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, in_tokens, out_tokens = await wf._profile(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["findings"] == []
        assert result["finding_count"] == 0
        assert result["files_scanned"] == 0
        assert result["by_impact"] == {"high": 0, "medium": 0, "low": 0}

    @pytest.mark.asyncio
    async def test_profile_detects_global_import(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test profiling detects wildcard import."""
        # Place file in a subdirectory so rglob finds it
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "mod.py"
        py_file.write_text("from os import *\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        global_findings = [f for f in result["findings"] if f["type"] == "global_import"]
        assert len(global_findings) >= 1
        assert global_findings[0]["impact"] == "low"

    @pytest.mark.asyncio
    async def test_profile_detects_repeated_regex(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test profiling detects non-compiled regex."""
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "util.py"
        py_file.write_text('import re\nre.search("pattern", text)\n')

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        regex_findings = [f for f in result["findings"] if f["type"] == "repeated_regex"]
        assert len(regex_findings) >= 1

    @pytest.mark.asyncio
    async def test_profile_detects_n_plus_one(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test profiling detects N+1 query pattern."""
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "app.py"
        # The n_plus_one pattern regex requires ".get(" on the SAME line as "for x in y:"
        py_file.write_text("for item in items: result = db.get(item.id)\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["files_scanned"] >= 1
        n_plus_one_findings = [f for f in result["findings"] if f["type"] == "n_plus_one"]
        assert len(n_plus_one_findings) >= 1

    @pytest.mark.asyncio
    async def test_profile_skips_excluded_dirs(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test profiling skips .git, node_modules, venv, etc."""
        venv_dir = scan_dir / "src" / "venv"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "lib.py"
        venv_file.write_text("from os import *\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["files_scanned"] == 0

    @pytest.mark.asyncio
    async def test_profile_nonexistent_path(self, cost_tracker: Any) -> None:
        """Test profiling a non-existent path returns empty results."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": "/nonexistent/path/xyz", "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["findings"] == []
        assert result["files_scanned"] == 0

    @pytest.mark.asyncio
    async def test_profile_with_auth_strategy_enabled(
        self,
        cost_tracker: Any,
        scan_dir: Path,
    ) -> None:
        """Test profile stage with auth strategy integration (mocked)."""
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "sample.py"
        py_file.write_text("x = 1\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=True)

        mock_strategy = MagicMock()
        mock_mode = MagicMock()
        mock_mode.value = "api"
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = 0.01

        mock_models = MagicMock()
        mock_models.count_lines_of_code = MagicMock(return_value=50)
        mock_models.get_auth_strategy = MagicMock(return_value=mock_strategy)
        mock_models.get_module_size_category = MagicMock(return_value="small")

        # Auth imports are local inside the method, so we mock via sys.modules.
        # We must also remove any previously-cached attune.models so the
        # ``from attune.models import …`` inside the method picks up our mock.
        import sys

        saved = sys.modules.get("attune.models")
        sys.modules["attune.models"] = mock_models
        try:
            result, _, _ = await wf._profile(
                {"path": str(scan_dir), "file_types": [".py"]},
                ModelTier.CHEAP,
            )
        finally:
            if saved is not None:
                sys.modules["attune.models"] = saved
            else:
                sys.modules.pop("attune.models", None)

        assert result["files_scanned"] >= 1
        assert wf._auth_mode_used == "api"

    @pytest.mark.asyncio
    async def test_profile_auth_strategy_subscription(
        self,
        cost_tracker: Any,
        scan_dir: Path,
    ) -> None:
        """Test profile with auth strategy recommending subscription mode."""
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "sample.py"
        py_file.write_text("x = 1\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=True)

        mock_strategy = MagicMock()
        mock_mode = MagicMock()
        mock_mode.value = "subscription"
        mock_strategy.get_recommended_mode.return_value = mock_mode
        mock_strategy.estimate_cost.return_value = 0.001

        mock_models = MagicMock()
        mock_models.count_lines_of_code = MagicMock(return_value=50)
        mock_models.get_auth_strategy = MagicMock(return_value=mock_strategy)
        mock_models.get_module_size_category = MagicMock(return_value="small")

        import sys

        saved = sys.modules.get("attune.models")
        sys.modules["attune.models"] = mock_models
        try:
            result, _, _ = await wf._profile(
                {"path": str(scan_dir), "file_types": [".py"]},
                ModelTier.CHEAP,
            )
        finally:
            if saved is not None:
                sys.modules["attune.models"] = saved
            else:
                sys.modules.pop("attune.models", None)

        assert wf._auth_mode_used == "subscription"

    @pytest.mark.asyncio
    async def test_profile_auth_strategy_import_error(
        self,
        cost_tracker: Any,
        scan_dir: Path,
    ) -> None:
        """Test profile handles ImportError from auth strategy gracefully."""
        sub = scan_dir / "src"
        sub.mkdir()
        py_file = sub / "sample.py"
        py_file.write_text("x = 1\n")

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=True)

        # Make ``from attune.models import count_lines_of_code, …`` raise
        # ImportError by injecting a mock with spec=[] (no attributes).
        bad_module = MagicMock(spec=[])

        import sys

        saved = sys.modules.get("attune.models")
        sys.modules["attune.models"] = bad_module
        try:
            result, _, _ = await wf._profile(
                {"path": str(scan_dir), "file_types": [".py"]},
                ModelTier.CHEAP,
            )
        finally:
            if saved is not None:
                sys.modules["attune.models"] = saved
            else:
                sys.modules.pop("attune.models", None)

        # Auth strategy failed gracefully; file scanning still happened.
        assert result["files_scanned"] >= 1
        # Auth mode was NOT set because the import failed.
        assert wf._auth_mode_used is None

    @pytest.mark.asyncio
    async def test_profile_groups_by_impact(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test profile correctly groups findings by impact level."""
        sub = scan_dir / "src"
        sub.mkdir()
        # n_plus_one regex needs ".get(" on the same line as the for-loop
        code = "from os import *\nfor item in items: result = db.get(item.id)\n"
        py_file = sub / "multi.py"
        py_file.write_text(code)

        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._profile(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        by_impact = result["by_impact"]
        assert "high" in by_impact
        assert "medium" in by_impact
        assert "low" in by_impact
        # Verify actual findings were detected
        assert result["files_scanned"] >= 1
        assert result["finding_count"] >= 2


@pytest.mark.unit
class TestPerfAuditAnalyze:
    """Tests for the _analyze stage."""

    @pytest.mark.asyncio
    async def test_analyze_empty_findings(self, cost_tracker: Any) -> None:
        """Test analyze with no findings produces empty analysis."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._analyze({"findings": []}, ModelTier.CAPABLE)
        assert result["analysis"] == []
        assert result["analyzed_files"] == 0

    @pytest.mark.asyncio
    async def test_analyze_groups_by_file(self, cost_tracker: Any) -> None:
        """Test analyze groups findings by file and scores correctly."""
        findings = [
            {"file": "a.py", "type": "n_plus_one", "impact": "high"},
            {"file": "a.py", "type": "sync_in_async", "impact": "high"},
            {"file": "b.py", "type": "global_import", "impact": "low"},
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._analyze({"findings": findings}, ModelTier.CAPABLE)
        analysis = result["analysis"]
        assert len(analysis) == 2
        assert result["analyzed_files"] == 2

        # a.py should have higher complexity score (2 high = 20)
        a_analysis = next(a for a in analysis if a["file"] == "a.py")
        assert a_analysis["complexity_score"] == 20
        assert a_analysis["high_impact"] == 2

        # b.py should have lower score (1 low = 1)
        b_analysis = next(a for a in analysis if a["file"] == "b.py")
        assert b_analysis["complexity_score"] == 1

    @pytest.mark.asyncio
    async def test_analyze_sorted_by_complexity(self, cost_tracker: Any) -> None:
        """Test analyze results are sorted by complexity (highest first)."""
        findings = [
            {"file": "low.py", "type": "global_import", "impact": "low"},
            {"file": "high.py", "type": "n_plus_one", "impact": "high"},
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._analyze({"findings": findings}, ModelTier.CAPABLE)
        analysis = result["analysis"]
        assert analysis[0]["file"] == "high.py"
        assert analysis[1]["file"] == "low.py"

    @pytest.mark.asyncio
    async def test_analyze_concerns_limited_to_5(self, cost_tracker: Any) -> None:
        """Test analyze limits concerns per file to 5."""
        findings = [{"file": "a.py", "type": f"type_{i}", "impact": "medium"} for i in range(8)]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._analyze({"findings": findings}, ModelTier.CAPABLE)
        for a in result["analysis"]:
            assert len(a["concerns"]) <= 5


@pytest.mark.unit
class TestPerfAuditHotspots:
    """Tests for the _hotspots stage."""

    @pytest.mark.asyncio
    async def test_hotspots_empty_analysis(self, cost_tracker: Any) -> None:
        """Test hotspots with empty analysis."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._hotspots({"analysis": []}, ModelTier.CAPABLE)
        hr = result["hotspot_result"]
        assert hr["hotspot_count"] == 0
        assert hr["perf_score"] == 100

    @pytest.mark.asyncio
    async def test_hotspots_identifies_critical(self, cost_tracker: Any) -> None:
        """Test hotspots identifies critical (score >= 20) files."""
        analysis = [
            {
                "file": "critical.py",
                "complexity_score": 25,
                "high_impact": 3,
                "concerns": ["n_plus_one"],
            },
            {
                "file": "moderate.py",
                "complexity_score": 15,
                "high_impact": 2,
                "concerns": ["regex"],
            },
            {
                "file": "ok.py",
                "complexity_score": 5,
                "high_impact": 0,
                "concerns": ["global_import"],
            },
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._hotspots({"analysis": analysis}, ModelTier.CAPABLE)
        hr = result["hotspot_result"]
        assert hr["hotspot_count"] == 2
        assert hr["critical_count"] == 1
        assert hr["moderate_count"] == 1

    @pytest.mark.asyncio
    async def test_hotspots_perf_score_critical(self, cost_tracker: Any) -> None:
        """Test hotspots sets perf_level to critical when score < 50."""
        analysis = [
            {"file": f"file_{i}.py", "complexity_score": 20, "high_impact": 2, "concerns": []}
            for i in range(5)
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._hotspots({"analysis": analysis}, ModelTier.CAPABLE)
        hr = result["hotspot_result"]
        assert hr["perf_score"] < 50
        assert hr["perf_level"] == "critical"

    @pytest.mark.asyncio
    async def test_hotspots_perf_score_good(self, cost_tracker: Any) -> None:
        """Test hotspots perf_level is good when score >= 75."""
        analysis = [
            {"file": "ok.py", "complexity_score": 2, "high_impact": 0, "concerns": []},
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._hotspots({"analysis": analysis}, ModelTier.CAPABLE)
        hr = result["hotspot_result"]
        assert hr["perf_score"] >= 75
        assert hr["perf_level"] == "good"

    @pytest.mark.asyncio
    async def test_hotspots_perf_score_warning(self, cost_tracker: Any) -> None:
        """Test hotspots perf_level is warning when 50 <= score < 75."""
        analysis = [
            {"file": f"file_{i}.py", "complexity_score": 10, "high_impact": 1, "concerns": []}
            for i in range(3)
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        result, _, _ = await wf._hotspots({"analysis": analysis}, ModelTier.CAPABLE)
        hr = result["hotspot_result"]
        # total_score = 30, max_score = 90 => 33% => perf_score = 67
        assert 50 <= hr["perf_score"] < 75
        assert hr["perf_level"] == "warning"

    @pytest.mark.asyncio
    async def test_hotspots_updates_hotspot_count(self, cost_tracker: Any) -> None:
        """Test that _hotspots updates self._hotspot_count."""
        analysis = [
            {"file": "a.py", "complexity_score": 15, "high_impact": 2, "concerns": []},
        ]
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        await wf._hotspots({"analysis": analysis}, ModelTier.CAPABLE)
        assert wf._hotspot_count == 1


@pytest.mark.unit
class TestPerfAuditOptimize:
    """Tests for the _optimize stage (LLM call)."""

    @pytest.mark.asyncio
    async def test_optimize_legacy_path(self, cost_tracker: Any) -> None:
        """Test optimize uses legacy _call_llm path."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        wf._executor = None
        wf._api_key = None

        input_data = {
            "hotspot_result": {
                "hotspots": [
                    {"file": "a.py", "complexity_score": 20, "concerns": ["n_plus_one"]},
                ],
                "perf_score": 70,
                "perf_level": "warning",
            },
            "findings": [
                {
                    "type": "n_plus_one",
                    "file": "a.py",
                    "line": 10,
                    "description": "N+1",
                    "impact": "high",
                },
            ],
            "target": "test-project",
            "files_scanned": 5,
            "finding_count": 1,
            "by_impact": {"high": 1, "medium": 0, "low": 0},
        }

        with (
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("Optimize batch queries", 100, 200),
            ),
            patch.object(wf, "_parse_xml_response", return_value={}),
            patch.object(wf, "_is_xml_enabled", return_value=False),
        ):
            result, in_tokens, out_tokens = await wf._optimize(input_data, ModelTier.PREMIUM)

        assert result["optimization_plan"] == "Optimize batch queries"
        assert result["perf_score"] == 70
        assert result["perf_level"] == "warning"
        assert result["model_tier_used"] == "premium"
        assert "formatted_report" in result
        assert "workflow_report" in result
        assert in_tokens == 100
        assert out_tokens == 200

    @pytest.mark.asyncio
    async def test_optimize_with_xml_enabled(self, cost_tracker: Any) -> None:
        """Test optimize uses XML-enhanced prompts."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        wf._executor = None
        wf._api_key = None

        input_data = {
            "hotspot_result": {"hotspots": [], "perf_score": 90, "perf_level": "good"},
            "findings": [],
            "target": "",
        }

        with (
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("XML response", 50, 100),
            ),
            patch.object(
                wf,
                "_parse_xml_response",
                return_value={
                    "xml_parsed": True,
                    "summary": "All good",
                    "findings": [],
                    "checklist": ["Check A"],
                },
            ),
            patch.object(wf, "_is_xml_enabled", return_value=True),
            patch.object(wf, "_render_xml_prompt", return_value="<xml>prompt</xml>"),
        ):
            result, _, _ = await wf._optimize(input_data, ModelTier.CAPABLE)

        assert result["xml_parsed"] is True
        assert result["summary"] == "All good"
        assert result["checklist"] == ["Check A"]

    @pytest.mark.asyncio
    async def test_optimize_executor_path(self, cost_tracker: Any) -> None:
        """Test optimize uses executor when available."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        wf._executor = MagicMock()
        wf._api_key = "test-key"

        input_data = {
            "hotspot_result": {"hotspots": [], "perf_score": 80, "perf_level": "good"},
            "findings": [],
            "target": "",
        }

        with (
            patch.object(
                wf,
                "run_step_with_executor",
                new_callable=AsyncMock,
                return_value=("Executor response", 30, 60, 0.01),
            ),
            patch.object(wf, "_parse_xml_response", return_value={}),
            patch.object(wf, "_is_xml_enabled", return_value=False),
        ):
            result, in_tokens, out_tokens = await wf._optimize(input_data, ModelTier.PREMIUM)

        assert result["optimization_plan"] == "Executor response"
        assert in_tokens == 30
        assert out_tokens == 60

    @pytest.mark.asyncio
    async def test_optimize_executor_fallback_to_legacy(self, cost_tracker: Any) -> None:
        """Test optimize falls back to _call_llm when executor fails."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        wf._executor = MagicMock()
        wf._api_key = "test-key"

        input_data = {
            "hotspot_result": {"hotspots": [], "perf_score": 80, "perf_level": "good"},
            "findings": [],
            "target": "",
        }

        with (
            patch.object(
                wf,
                "run_step_with_executor",
                new_callable=AsyncMock,
                side_effect=RuntimeError("executor failed"),
            ),
            patch.object(
                wf,
                "_call_llm",
                new_callable=AsyncMock,
                return_value=("Fallback response", 40, 80),
            ),
            patch.object(wf, "_parse_xml_response", return_value={}),
            patch.object(wf, "_is_xml_enabled", return_value=False),
        ):
            result, in_tokens, out_tokens = await wf._optimize(input_data, ModelTier.PREMIUM)

        assert result["optimization_plan"] == "Fallback response"
        assert in_tokens == 40


@pytest.mark.unit
class TestPerfAuditGetOptimizationAction:
    """Tests for _get_optimization_action helper."""

    def test_known_concerns(self, cost_tracker: Any) -> None:
        """Test known concern types return action dicts."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        known = [
            "n_plus_one",
            "sync_in_async",
            "string_concat_loop",
            "repeated_regex",
            "nested_loops",
            "list_comprehension_in_loop",
            "global_import",
        ]
        for concern in known:
            action = wf._get_optimization_action(concern)
            assert action is not None, f"Missing action for {concern}"
            assert "action" in action
            assert "description" in action
            assert "estimated_impact" in action

    def test_unknown_concern_returns_none(self, cost_tracker: Any) -> None:
        """Test unknown concern type returns None."""
        wf = PerformanceAuditWorkflow(cost_tracker=cost_tracker, enable_auth_strategy=False)
        assert wf._get_optimization_action("unknown_pattern") is None


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


# ============================================================================
# TestGenerationWorkflow Tests
# ============================================================================


@pytest.mark.unit
class TestTestGenWorkflowInit:
    """Tests for TestGenerationWorkflow initialization."""

    def test_default_initialization(self, cost_tracker: Any) -> None:
        """Test default workflow initialization."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        assert wf.name == "test-gen"
        assert wf.min_tests_for_review == 10
        assert wf.write_tests is False
        assert wf.output_dir == "tests/generated"
        assert wf.enable_auth_strategy is True
        assert wf._test_count == 0
        assert wf._bug_hotspots == []

    def test_custom_initialization(self, cost_tracker: Any) -> None:
        """Test workflow with custom parameters."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_tests_for_review=5,
            write_tests=True,
            output_dir="custom_tests",
            enable_auth_strategy=False,
        )
        assert wf.min_tests_for_review == 5
        assert wf.write_tests is True
        assert wf.output_dir == "custom_tests"
        assert wf.enable_auth_strategy is False

    def test_stages_and_tier_map(self, cost_tracker: Any) -> None:
        """Verify stages and tier mappings."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        assert wf.stages == ["identify", "analyze", "generate", "review"]
        assert wf.tier_map["identify"] == ModelTier.CHEAP
        assert wf.tier_map["analyze"] == ModelTier.CAPABLE
        assert wf.tier_map["generate"] == ModelTier.CAPABLE
        assert wf.tier_map["review"] == ModelTier.PREMIUM

    def test_load_bug_hotspots_from_file(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test loading bug hotspots from debugging.json."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debugging_file = patterns_dir / "debugging.json"
        debugging_file.write_text(
            json.dumps(
                {
                    "patterns": [
                        {"files_affected": ["src/auth.py", "src/db.py"]},
                        {"files_affected": ["src/auth.py", None]},
                    ],
                },
            ),
        )
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir=str(patterns_dir),
        )
        assert "src/auth.py" in wf._bug_hotspots
        assert "src/db.py" in wf._bug_hotspots

    def test_load_bug_hotspots_missing_file(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test missing debugging.json is handled gracefully."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir=str(tmp_path))
        assert wf._bug_hotspots == []

    def test_load_bug_hotspots_invalid_json(self, tmp_path: Path, cost_tracker: Any) -> None:
        """Test invalid JSON in debugging.json is handled gracefully."""
        patterns_dir = tmp_path / "patterns"
        patterns_dir.mkdir()
        debugging_file = patterns_dir / "debugging.json"
        debugging_file.write_text("{broken json")
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir=str(patterns_dir),
        )
        assert wf._bug_hotspots == []


@pytest.mark.unit
class TestTestGenShouldSkipStage:
    """Tests for conditional stage skipping."""

    def test_review_downgrade_few_tests(self, cost_tracker: Any) -> None:
        """Test review downgrades to CAPABLE with few tests generated."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_tests_for_review=10,
        )
        wf._test_count = 3
        should_skip, reason = wf.should_skip_stage("review", {})
        assert should_skip is False
        assert reason is None
        assert wf.tier_map["review"] == ModelTier.CAPABLE

    def test_review_stays_premium_enough_tests(self, cost_tracker: Any) -> None:
        """Test review stays PREMIUM with enough tests."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            min_tests_for_review=10,
        )
        # Reset tier_map since class-level dict may have been mutated
        wf.tier_map["review"] = ModelTier.PREMIUM
        wf._test_count = 15
        should_skip, reason = wf.should_skip_stage("review", {})
        assert should_skip is False
        assert wf.tier_map["review"] == ModelTier.PREMIUM

    def test_non_review_stage_not_skipped(self, cost_tracker: Any) -> None:
        """Test non-review stages are never skipped."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        for stage in ["identify", "analyze", "generate"]:
            should_skip, reason = wf.should_skip_stage(stage, {})
            assert should_skip is False


@pytest.mark.unit
class TestTestGenRunStage:
    """Tests for run_stage dispatch."""

    @pytest.mark.asyncio
    async def test_run_stage_unknown_raises(self, cost_tracker: Any) -> None:
        """Test run_stage raises ValueError for unknown stage."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        with pytest.raises(ValueError, match="Unknown stage: bogus"):
            await wf.run_stage("bogus", ModelTier.CHEAP, {})

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_identify(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _identify."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        with patch.object(wf, "_identify", new_callable=AsyncMock) as mock:
            mock.return_value = ({}, 1, 1)
            await wf.run_stage("identify", ModelTier.CHEAP, {})
            mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_analyze(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _analyze."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        with patch.object(wf, "_analyze", new_callable=AsyncMock) as mock:
            mock.return_value = ({}, 1, 1)
            await wf.run_stage("analyze", ModelTier.CAPABLE, {})
            mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_stage_dispatches_generate(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _generate."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        with patch.object(wf, "_generate", new_callable=AsyncMock) as mock:
            mock.return_value = ({}, 1, 1)
            await wf.run_stage("generate", ModelTier.CAPABLE, {})
            mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_stage_review_calls_review(self, cost_tracker: Any) -> None:
        """Test run_stage routes to _review (method may not be defined)."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        with patch.object(wf, "_review", new_callable=AsyncMock, create=True) as mock:
            mock.return_value = ({}, 1, 1)
            await wf.run_stage("review", ModelTier.PREMIUM, {})
            mock.assert_awaited_once()


@pytest.mark.unit
class TestTestGenIdentify:
    """Tests for the _identify stage.

    Note: The _identify method has a known scoping issue where 'from pathlib import Path'
    is done inside the auth strategy try block. When enable_auth_strategy=True, we must
    ensure the auth code path runs so that Path is bound locally. We mock the auth
    imports to make them raise, which triggers the except block and then the rest
    of the method uses the module-level Path.
    """

    @pytest.mark.asyncio
    async def test_identify_empty_directory(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test identifying files in empty directory."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        # Auth strategy will fail because attune.models functions aren't available
        # but that's fine - the except block handles it
        result, _, _ = await wf._identify(
            {"path": str(tmp_path), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_candidates"] == 0
        assert result["candidates"] == []

    @pytest.mark.asyncio
    async def test_identify_finds_untested_files(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test identify finds files without tests."""
        sub = scan_dir / "src"
        sub.mkdir()
        code = "\n".join([f"def func_{i}(): pass" for i in range(120)])
        src_file = sub / "module.py"
        src_file.write_text(code)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_candidates"] >= 1
        assert result["untested_count"] >= 1
        candidate = result["candidates"][0]
        assert candidate["priority"] >= 40  # 30 no tests + 10 >100 lines
        assert candidate["has_tests"] is False

    @pytest.mark.asyncio
    async def test_identify_skips_test_files(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test identify skips existing test files."""
        sub = scan_dir / "src"
        sub.mkdir()
        tf = sub / "test_module.py"
        tf.write_text("def test_something(): pass\n")
        src_file = sub / "module.py"
        src_file.write_text("def func(): pass\n" * 50)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["existing_test_files"] >= 1
        candidate_files = [c["file"] for c in result["candidates"]]
        # No candidate should be a test file
        for f in candidate_files:
            assert "test_" not in Path(f).name

    @pytest.mark.asyncio
    async def test_identify_bug_hotspot_priority(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test identify gives higher priority to bug hotspots."""
        sub = scan_dir / "src"
        sub.mkdir()
        src_file = sub / "buggy.py"
        src_file.write_text("x = 1\n" * 110)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        wf._bug_hotspots = [str(src_file)]

        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["hotspot_count"] >= 1
        candidate = result["candidates"][0]
        assert candidate["is_hotspot"] is True
        assert candidate["priority"] >= 90  # hotspot(50) + no tests(30) + >100 lines(10)

    @pytest.mark.asyncio
    async def test_identify_respects_max_candidates(
        self,
        cost_tracker: Any,
        scan_dir: Path,
    ) -> None:
        """Test identify limits candidates to max_candidates."""
        sub = scan_dir / "src"
        sub.mkdir()
        for i in range(10):
            f = sub / f"mod_{i}.py"
            f.write_text("def func(): pass\n" * 110)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"], "max_candidates": 3},
            ModelTier.CHEAP,
        )
        assert len(result["candidates"]) <= 3
        assert result["total_candidates"] >= 10

    @pytest.mark.asyncio
    async def test_identify_respects_max_files_to_scan(
        self,
        cost_tracker: Any,
        scan_dir: Path,
    ) -> None:
        """Test identify stops scanning at max_files_to_scan limit."""
        sub = scan_dir / "src"
        sub.mkdir()
        for i in range(10):
            f = sub / f"mod_{i}.py"
            f.write_text("x = 1\n" * 110)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"], "max_files_to_scan": 3},
            ModelTier.CHEAP,
        )
        scan_summary = result["scan_summary"]
        assert scan_summary["files_scanned"] <= 3
        assert scan_summary["early_exit_reason"] is not None

    @pytest.mark.asyncio
    async def test_identify_skips_large_files(self, cost_tracker: Any, scan_dir: Path) -> None:
        """Test identify skips files larger than max_file_size_kb."""
        sub = scan_dir / "src"
        sub.mkdir()
        large_file = sub / "large.py"
        large_file.write_text("x = 1\n" * 50000)

        small_file = sub / "small.py"
        small_file.write_text("x = 1\n" * 110)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": str(scan_dir), "file_types": [".py"], "max_file_size_kb": 1},
            ModelTier.CHEAP,
        )
        scan_summary = result["scan_summary"]
        assert scan_summary["files_too_large"] >= 1

    @pytest.mark.asyncio
    async def test_identify_nonexistent_path(self, cost_tracker: Any) -> None:
        """Test identify with nonexistent path."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {"path": "/nonexistent/xyz", "file_types": [".py"]},
            ModelTier.CHEAP,
        )
        assert result["total_candidates"] == 0

    @pytest.mark.asyncio
    async def test_identify_config_passthrough(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test identify passes config through to subsequent stages."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=True,
        )
        result, _, _ = await wf._identify(
            {
                "path": str(tmp_path),
                "file_types": [".py"],
                "max_files_to_analyze": 5,
                "max_functions_per_file": 10,
            },
            ModelTier.CHEAP,
        )
        config = result["config"]
        assert config["max_files_to_analyze"] == 5
        assert config["max_functions_per_file"] == 10


@pytest.mark.unit
class TestTestGenFindTestFile:
    """Tests for _find_test_file helper."""

    def test_find_existing_test_file(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test finding an existing test file."""
        src_file = tmp_path / "module.py"
        src_file.write_text("x = 1\n")
        test_file = tmp_path / "test_module.py"
        test_file.write_text("def test_x(): pass\n")

        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        found = wf._find_test_file(src_file)
        assert found is not None
        assert found.exists()

    def test_find_test_file_in_tests_subdir(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test finding test file in tests/ subdirectory."""
        src_file = tmp_path / "module.py"
        src_file.write_text("x = 1\n")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_module.py"
        test_file.write_text("def test_x(): pass\n")

        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        found = wf._find_test_file(src_file)
        assert found is not None
        assert found.exists()

    def test_find_test_file_returns_expected_path_when_missing(
        self,
        cost_tracker: Any,
        tmp_path: Path,
    ) -> None:
        """Test returns expected path even when test file doesn't exist."""
        src_file = tmp_path / "module.py"
        src_file.write_text("x = 1\n")

        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        found = wf._find_test_file(src_file)
        assert found is not None
        assert found.name == "test_module.py"


@pytest.mark.unit
class TestTestGenAnalyze:
    """Tests for the _analyze stage."""

    @pytest.mark.asyncio
    async def test_analyze_empty_candidates(self, cost_tracker: Any) -> None:
        """Test analyze with no candidates."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        result, _, _ = await wf._analyze({"candidates": [], "config": {}}, ModelTier.CAPABLE)
        assert result["analysis"] == []
        assert result["total_functions"] == 0
        assert result["total_classes"] == 0

    @pytest.mark.asyncio
    async def test_analyze_extracts_functions(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test analyze extracts functions from Python files."""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y
'''
        src_file = tmp_path / "math_utils.py"
        src_file.write_text(code)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        candidates = [{"file": str(src_file), "priority": 50}]
        result, _, _ = await wf._analyze(
            {"candidates": candidates, "config": {}},
            ModelTier.CAPABLE,
        )
        assert len(result["analysis"]) == 1
        assert result["total_functions"] >= 2

    @pytest.mark.asyncio
    async def test_analyze_extracts_classes(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test analyze extracts classes from Python files."""
        code = '''
class Calculator:
    """A simple calculator."""

    def __init__(self):
        self.result = 0

    def add(self, x: int) -> int:
        self.result += x
        return self.result
'''
        src_file = tmp_path / "calculator.py"
        src_file.write_text(code)

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        candidates = [{"file": str(src_file), "priority": 50}]
        result, _, _ = await wf._analyze(
            {"candidates": candidates, "config": {}},
            ModelTier.CAPABLE,
        )
        assert result["total_classes"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_handles_syntax_errors(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test analyze handles files with syntax errors."""
        src_file = tmp_path / "broken.py"
        src_file.write_text("def broken(:\n    pass\n")

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        candidates = [{"file": str(src_file), "priority": 50}]
        result, _, _ = await wf._analyze(
            {"candidates": candidates, "config": {}},
            ModelTier.CAPABLE,
        )
        assert len(result["analysis"]) == 1
        assert result["parse_errors"] != []

    @pytest.mark.asyncio
    async def test_analyze_skips_missing_files(self, cost_tracker: Any) -> None:
        """Test analyze skips files that don't exist."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        candidates = [{"file": "/nonexistent/file.py", "priority": 50}]
        result, _, _ = await wf._analyze(
            {"candidates": candidates, "config": {}},
            ModelTier.CAPABLE,
        )
        assert result["analysis"] == []

    @pytest.mark.asyncio
    async def test_analyze_respects_max_files_to_analyze(
        self,
        cost_tracker: Any,
        tmp_path: Path,
    ) -> None:
        """Test analyze limits files analyzed to config value."""
        for i in range(5):
            f = tmp_path / f"mod_{i}.py"
            f.write_text(f"def func_{i}(): pass\n")

        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        candidates = [{"file": str(tmp_path / f"mod_{i}.py"), "priority": 50} for i in range(5)]
        result, _, _ = await wf._analyze(
            {"candidates": candidates, "config": {"max_files_to_analyze": 2}},
            ModelTier.CAPABLE,
        )
        assert len(result["analysis"]) <= 2


@pytest.mark.unit
class TestTestGenGenerateSuggestions:
    """Tests for _generate_suggestions helper."""

    def test_suggestions_for_functions(self, cost_tracker: Any) -> None:
        """Test suggestion generation for functions."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        functions = [
            {"name": "add", "params": [("a", "int", None)], "is_async": False},
            {"name": "fetch", "params": [("url", "str", None)], "is_async": True},
        ]
        suggestions = wf._generate_suggestions(functions, [])
        assert any("add" in s for s in suggestions)
        assert any("async" in s.lower() for s in suggestions)

    def test_suggestions_for_classes(self, cost_tracker: Any) -> None:
        """Test suggestion generation for classes."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        classes = [{"name": "Calculator", "methods": []}]
        suggestions = wf._generate_suggestions([], classes)
        assert any("Calculator" in s for s in suggestions)

    def test_suggestions_empty_input(self, cost_tracker: Any) -> None:
        """Test suggestion generation with empty input."""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        suggestions = wf._generate_suggestions([], [])
        assert suggestions == []


@pytest.mark.unit
class TestTestGenGenerate:
    """Tests for the _generate stage."""

    @pytest.mark.asyncio
    async def test_generate_empty_analysis(self, cost_tracker: Any) -> None:
        """Test generate with no analysis results."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        result, _, _ = await wf._generate({"analysis": [], "config": {}}, ModelTier.CAPABLE)
        assert result["generated_tests"] == []
        assert result["total_tests_generated"] == 0
        assert result["written_files"] == []

    @pytest.mark.asyncio
    async def test_generate_creates_function_tests(self, cost_tracker: Any) -> None:
        """Test generate creates tests for functions."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        analysis = [
            {
                "file": "src/math_utils.py",
                "priority": 50,
                "functions": [
                    {
                        "name": "add",
                        "params": [("a", "int", None), ("b", "int", None)],
                        "param_names": ["a", "b"],
                        "is_async": False,
                        "return_type": "int",
                        "raises": [],
                        "has_side_effects": False,
                        "complexity": 1,
                        "docstring": "Add numbers.",
                    },
                ],
                "classes": [],
            },
        ]
        result, _, _ = await wf._generate({"analysis": analysis, "config": {}}, ModelTier.CAPABLE)
        assert len(result["generated_tests"]) == 1
        assert result["total_tests_generated"] >= 1
        assert result["generated_tests"][0]["test_file"] == "test_math_utils.py"

    @pytest.mark.asyncio
    async def test_generate_creates_class_tests(self, cost_tracker: Any) -> None:
        """Test generate creates tests for classes."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        analysis = [
            {
                "file": "src/calculator.py",
                "priority": 50,
                "functions": [],
                "classes": [
                    {
                        "name": "Calculator",
                        "init_params": [],
                        "methods": [
                            {
                                "name": "add",
                                "params": [("x", "int", None)],
                                "is_async": False,
                                "raises": [],
                            },
                        ],
                        "base_classes": [],
                        "docstring": "Calculator class.",
                        "is_dataclass": False,
                        "required_init_params": 0,
                    },
                ],
            },
        ]
        result, _, _ = await wf._generate({"analysis": analysis, "config": {}}, ModelTier.CAPABLE)
        assert result["total_tests_generated"] >= 1
        tests = result["generated_tests"][0]["tests"]
        class_tests = [t for t in tests if t["type"] == "class"]
        assert len(class_tests) >= 1

    @pytest.mark.asyncio
    async def test_generate_writes_test_files(self, cost_tracker: Any, tmp_path: Path) -> None:
        """Test generate writes tests to disk when write_tests=True."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
            write_tests=True,
            output_dir=str(tmp_path / "generated"),
        )
        analysis = [
            {
                "file": "src/utils.py",
                "priority": 50,
                "functions": [
                    {
                        "name": "helper",
                        "params": [],
                        "param_names": [],
                        "is_async": False,
                        "return_type": "str",
                        "raises": [],
                        "has_side_effects": False,
                        "complexity": 1,
                        "docstring": None,
                    },
                ],
                "classes": [],
            },
        ]
        result, _, _ = await wf._generate({"analysis": analysis, "config": {}}, ModelTier.CAPABLE)
        assert result["tests_written"] is True
        assert len(result["written_files"]) >= 1
        written_path = Path(result["written_files"][0])
        assert written_path.exists()

    @pytest.mark.asyncio
    async def test_generate_respects_limits(self, cost_tracker: Any) -> None:
        """Test generate respects max files/functions/classes limits."""
        wf = TestGenerationWorkflow(
            cost_tracker=cost_tracker,
            patterns_dir="/nonexistent",
            enable_auth_strategy=False,
        )
        analysis = [
            {
                "file": f"src/mod_{i}.py",
                "priority": 50,
                "functions": [
                    {
                        "name": f"func_{j}",
                        "params": [],
                        "param_names": [],
                        "is_async": False,
                        "return_type": None,
                        "raises": [],
                        "has_side_effects": False,
                        "complexity": 1,
                        "docstring": None,
                    }
                    for j in range(10)
                ],
                "classes": [],
            }
            for i in range(20)
        ]
        result, _, _ = await wf._generate(
            {
                "analysis": analysis,
                "config": {"max_files_to_generate": 2, "max_functions_to_generate": 3},
            },
            ModelTier.CAPABLE,
        )
        assert len(result["generated_tests"]) <= 2
        for gt in result["generated_tests"]:
            func_tests = [t for t in gt["tests"] if t["type"] == "function"]
            assert len(func_tests) <= 3


@pytest.mark.unit
class TestTestGenExtractFunctions:
    """Tests for _extract_functions helper."""

    def test_extract_public_functions(self, cost_tracker: Any) -> None:
        """Test extracting public functions from code."""
        code = '''
def public_func(x: int) -> int:
    """A public function."""
    return x + 1

def __dunder_func__():
    pass
'''
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        functions, error = wf._extract_functions(code)
        names = [f["name"] for f in functions]
        assert "public_func" in names
        assert "__dunder_func__" in names
        assert error is None

    def test_extract_functions_syntax_error(self, cost_tracker: Any) -> None:
        """Test extracting functions from invalid code returns empty list."""
        code = "def broken(:\n    pass\n"
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        functions, error = wf._extract_functions(code, "broken.py")
        assert functions == []
        assert error is not None
        assert "SyntaxError" in error

    def test_extract_functions_respects_max(self, cost_tracker: Any) -> None:
        """Test function extraction respects max limit."""
        code = "\n".join([f"def func_{i}(): pass" for i in range(50)])
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        functions, _ = wf._extract_functions(code, max_functions=5)
        assert len(functions) <= 5


@pytest.mark.unit
class TestTestGenExtractClasses:
    """Tests for _extract_classes helper."""

    def test_extract_regular_class(self, cost_tracker: Any) -> None:
        """Test extracting a regular class."""
        code = '''
class MyClass:
    """A test class."""

    def __init__(self, x: int):
        self.x = x

    def get_x(self) -> int:
        return self.x
'''
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        classes, error = wf._extract_classes(code)
        assert len(classes) == 1
        assert classes[0]["name"] == "MyClass"
        assert error is None

    def test_extract_classes_syntax_error(self, cost_tracker: Any) -> None:
        """Test extracting classes from invalid code returns empty list."""
        code = "class Broken(:\n    pass\n"
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        classes, error = wf._extract_classes(code, "broken.py")
        assert classes == []
        assert error is not None

    def test_extract_classes_respects_max(self, cost_tracker: Any) -> None:
        """Test class extraction respects max limit."""
        code = "\n".join([f"class Cls{i}:\n    pass\n" for i in range(20)])
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        classes, _ = wf._extract_classes(code, max_classes=3)
        assert len(classes) <= 3

    def test_extract_skips_enums(self, cost_tracker: Any) -> None:
        """Test that enum classes are skipped."""
        code = """
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
"""
        wf = TestGenerationWorkflow(cost_tracker=cost_tracker, patterns_dir="/nonexistent")
        classes, _ = wf._extract_classes(code)
        assert len(classes) == 0
