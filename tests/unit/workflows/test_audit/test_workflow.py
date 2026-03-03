"""Tests for TestAuditWorkflow.

Covers:
- Class attributes (name, description, stages, tier_map)
- Constructor defaults and custom parameters
- Audit stage: subprocess mock, coverage parsing, module prioritization
- Plan stage: batch grouping and XML task spec generation
- Execute stage: quick mode skip, deep mode batch results
- Verify stage: subprocess mock, delta calculation

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.models import ModelTier
from attune.workflows.test_audit.coverage_parser import ModuleCoverage
from attune.workflows.test_audit.workflow import (
    TestAuditWorkflow,
    _build_batch_result,
    _dict_to_module,
    _module_to_dict,
    _summarize_missing,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(
    path: str = "src/attune/foo.py",
    stmts: int = 100,
    covered: int = 40,
    missing_lines: list[int] | None = None,
    pct: float = 40.0,
    priority: float = 60.0,
) -> ModuleCoverage:
    """Return a ModuleCoverage with sensible defaults."""
    return ModuleCoverage(
        path=path,
        stmts=stmts,
        covered=covered,
        missing_lines=missing_lines or [10, 20, 30],
        pct=pct,
        priority=priority,
    )


def _make_coverage_json(tmp_path: Path, files: dict) -> str:
    """Write a coverage.json file and return its path."""
    data = {"files": files}
    cov_path = tmp_path / "coverage.json"
    cov_path.write_text(json.dumps(data), encoding="utf-8")
    return str(cov_path)


# ---------------------------------------------------------------------------
# TestAuditWorkflowConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditWorkflowConfig:
    """Verify class-level attributes on TestAuditWorkflow."""

    def test_name(self):
        """Class attribute 'name' should be 'test-audit'."""
        assert TestAuditWorkflow.name == "test-audit"

    def test_description(self):
        """Class attribute 'description' should be non-empty."""
        assert TestAuditWorkflow.description
        assert isinstance(TestAuditWorkflow.description, str)

    def test_stages(self):
        """Stages list should contain the four expected stage names."""
        assert TestAuditWorkflow.stages == ["audit", "plan", "execute", "verify"]

    def test_tier_map_keys(self):
        """tier_map should have one entry per stage."""
        expected_keys = {"audit", "plan", "execute", "verify"}
        assert set(TestAuditWorkflow.tier_map.keys()) == expected_keys

    def test_tier_map_audit_is_cheap(self):
        """Audit stage uses CHEAP model tier."""
        assert TestAuditWorkflow.tier_map["audit"] == ModelTier.CHEAP

    def test_tier_map_plan_is_capable(self):
        """Plan stage uses CAPABLE model tier."""
        assert TestAuditWorkflow.tier_map["plan"] == ModelTier.CAPABLE

    def test_tier_map_execute_is_capable(self):
        """Execute stage uses CAPABLE model tier."""
        assert TestAuditWorkflow.tier_map["execute"] == ModelTier.CAPABLE

    def test_tier_map_verify_is_cheap(self):
        """Verify stage uses CHEAP model tier."""
        assert TestAuditWorkflow.tier_map["verify"] == ModelTier.CHEAP


# ---------------------------------------------------------------------------
# TestAuditWorkflowInit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditWorkflowInit:
    """Test constructor defaults and custom parameter assignment."""

    def test_defaults(self):
        """Default constructor sets expected attribute values."""
        wf = TestAuditWorkflow()
        assert wf.target_coverage == 90.0
        assert wf.min_module_coverage == 50.0
        assert wf.max_batches == 5
        assert wf.batch_parallelism == 3
        assert wf.mode == "deep"
        assert wf._coverage_before is None

    def test_custom_target_coverage(self):
        """Custom target_coverage is stored correctly."""
        wf = TestAuditWorkflow(target_coverage=80.0)
        assert wf.target_coverage == 80.0

    def test_custom_min_module_coverage(self):
        """Custom min_module_coverage is stored correctly."""
        wf = TestAuditWorkflow(min_module_coverage=30.0)
        assert wf.min_module_coverage == 30.0

    def test_custom_max_batches(self):
        """Custom max_batches is stored correctly."""
        wf = TestAuditWorkflow(max_batches=10)
        assert wf.max_batches == 10

    def test_custom_batch_parallelism(self):
        """Custom batch_parallelism is stored correctly."""
        wf = TestAuditWorkflow(batch_parallelism=6)
        assert wf.batch_parallelism == 6

    def test_mode_quick(self):
        """Mode 'quick' is stored correctly."""
        wf = TestAuditWorkflow(mode="quick")
        assert wf.mode == "quick"

    def test_mode_deep(self):
        """Mode 'deep' is stored correctly."""
        wf = TestAuditWorkflow(mode="deep")
        assert wf.mode == "deep"

    def test_has_logger(self):
        """Workflow instance should have a logger attribute from BaseWorkflow."""
        wf = TestAuditWorkflow()
        assert hasattr(wf, "logger")


# ---------------------------------------------------------------------------
# TestAuditStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuditStage:
    """Tests for the _audit stage."""

    @pytest.mark.asyncio
    async def test_audit_returns_tuple(self, tmp_path):
        """Audit stage returns a (dict, int, int) tuple."""
        cov_data = {
            "src/attune/foo.py": {
                "summary": {"num_statements": 100, "covered_lines": 30},
                "missing_lines": list(range(70)),
            }
        }
        _make_coverage_json(tmp_path, cov_data)

        wf = TestAuditWorkflow(min_module_coverage=50.0)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[
                    ModuleCoverage(
                        path="src/attune/foo.py",
                        stmts=100,
                        covered=30,
                        missing_lines=list(range(70)),
                        pct=30.0,
                        priority=70.0,
                    )
                ],
            ),
        ):
            result, in_tok, out_tok = await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert isinstance(result, dict)
        assert isinstance(in_tok, int)
        assert isinstance(out_tok, int)

    @pytest.mark.asyncio
    async def test_audit_output_has_modules_key(self, tmp_path):
        """Audit output dict contains a 'modules' list."""
        wf = TestAuditWorkflow(min_module_coverage=50.0)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules = [
            ModuleCoverage(
                path="src/attune/foo.py",
                stmts=100,
                covered=30,
                missing_lines=list(range(70)),
                pct=30.0,
                priority=70.0,
            )
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules,
            ),
        ):
            result, _, _ = await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert "modules" in result
        assert isinstance(result["modules"], list)
        assert len(result["modules"]) == 1
        assert result["modules"][0]["path"] == "src/attune/foo.py"

    @pytest.mark.asyncio
    async def test_audit_filters_above_threshold(self):
        """Modules above min_module_coverage are excluded."""
        wf = TestAuditWorkflow(min_module_coverage=50.0)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules = [
            ModuleCoverage(
                path="src/attune/low.py",
                stmts=100,
                covered=20,
                missing_lines=[],
                pct=20.0,
                priority=80.0,
            ),
            ModuleCoverage(
                path="src/attune/high.py",
                stmts=100,
                covered=90,
                missing_lines=[],
                pct=90.0,
                priority=10.0,
            ),
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules,
            ),
        ):
            result, _, _ = await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        paths = [m["path"] for m in result["modules"]]
        assert "src/attune/low.py" in paths
        assert "src/attune/high.py" not in paths

    @pytest.mark.asyncio
    async def test_audit_stores_coverage_before(self):
        """Audit stage stores overall coverage percentage in _coverage_before."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules = [
            ModuleCoverage(
                path="src/attune/foo.py",
                stmts=100,
                covered=75,
                missing_lines=[],
                pct=75.0,
                priority=25.0,
            )
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules,
            ),
        ):
            await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert wf._coverage_before == pytest.approx(75.0)

    @pytest.mark.asyncio
    async def test_audit_handles_subprocess_error_gracefully(self):
        """Audit stage returns empty modules list on subprocess failure."""
        wf = TestAuditWorkflow()

        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("process failed"),
        ):
            result, _, _ = await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert result["modules"] == []
        assert result["total_modules"] == 0

    @pytest.mark.asyncio
    async def test_audit_nonzero_returncode_still_parses(self):
        """Exit code 1 (test failures) still allows coverage parsing."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules = [
            ModuleCoverage(
                path="src/attune/x.py",
                stmts=50,
                covered=10,
                missing_lines=[],
                pct=20.0,
                priority=40.0,
            )
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules,
            ),
        ):
            result, _, _ = await wf._audit({}, ModelTier.CHEAP)

        assert result["total_modules"] == 1

    @pytest.mark.asyncio
    async def test_audit_output_includes_input_data(self):
        """Audit output dict merges the original input_data."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, _, _ = await wf._audit(
                {"src_path": "src/attune", "extra_key": "sentinel"},
                ModelTier.CHEAP,
            )

        assert result.get("extra_key") == "sentinel"
        assert result.get("src_path") == "src/attune"


# ---------------------------------------------------------------------------
# TestPlanStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlanStage:
    """Tests for the _plan stage."""

    @pytest.mark.asyncio
    async def test_plan_returns_tuple(self):
        """Plan stage returns a (dict, int, int) tuple."""
        wf = TestAuditWorkflow(max_batches=3)
        modules = [_module_to_dict(_make_module())]
        result, in_tok, out_tok = await wf._plan({"modules": modules}, ModelTier.CAPABLE)
        assert isinstance(result, dict)
        assert isinstance(in_tok, int)
        assert isinstance(out_tok, int)

    @pytest.mark.asyncio
    async def test_plan_produces_batches_key(self):
        """Plan output contains a 'batches' list."""
        wf = TestAuditWorkflow()
        modules = [_module_to_dict(_make_module())]
        result, _, _ = await wf._plan({"modules": modules}, ModelTier.CAPABLE)
        assert "batches" in result
        assert isinstance(result["batches"], list)

    @pytest.mark.asyncio
    async def test_plan_batch_has_task_xml(self):
        """Each batch spec in the plan contains a non-empty task_xml field."""
        wf = TestAuditWorkflow()
        modules = [_module_to_dict(_make_module())]
        result, _, _ = await wf._plan({"modules": modules}, ModelTier.CAPABLE)
        for batch in result["batches"]:
            assert "task_xml" in batch
            assert batch["task_xml"].strip()

    @pytest.mark.asyncio
    async def test_plan_batch_has_batch_id(self):
        """Each batch spec contains a batch_id string."""
        wf = TestAuditWorkflow()
        modules = [_module_to_dict(_make_module())]
        result, _, _ = await wf._plan({"modules": modules}, ModelTier.CAPABLE)
        for batch in result["batches"]:
            assert "batch_id" in batch
            assert batch["batch_id"].startswith("batch_")

    @pytest.mark.asyncio
    async def test_plan_empty_modules_produces_no_batches(self):
        """Empty module list results in zero batches."""
        wf = TestAuditWorkflow()
        result, _, _ = await wf._plan({"modules": []}, ModelTier.CAPABLE)
        assert result["batches"] == []
        assert result["total_batches"] == 0

    @pytest.mark.asyncio
    async def test_plan_respects_max_batches(self):
        """Number of batches is capped at max_batches."""
        wf = TestAuditWorkflow(max_batches=2)
        modules = [
            _module_to_dict(
                _make_module(path=f"src/attune/pkg{i}/module.py", pct=10.0, priority=90.0)
            )
            for i in range(10)
        ]
        result, _, _ = await wf._plan({"modules": modules}, ModelTier.CAPABLE)
        assert len(result["batches"]) <= 2

    @pytest.mark.asyncio
    async def test_plan_merges_input_data(self):
        """Plan output includes all keys from input_data."""
        wf = TestAuditWorkflow()
        result, _, _ = await wf._plan(
            {"modules": [], "extra": "value"},
            ModelTier.CAPABLE,
        )
        assert result.get("extra") == "value"


# ---------------------------------------------------------------------------
# TestExecuteStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecuteStage:
    """Tests for the _execute_stage stage."""

    @pytest.mark.asyncio
    async def test_quick_mode_skips_execution(self):
        """In 'quick' mode, execute stage returns empty results list."""
        wf = TestAuditWorkflow(mode="quick")
        result, in_tok, out_tok = await wf._execute_stage(
            {"batches": [{"batch_id": "batch_0", "modules": []}]},
            ModelTier.CAPABLE,
        )
        assert result["results"] == []
        assert result["mode"] == "quick"
        assert in_tok == 0
        assert out_tok == 0

    @pytest.mark.asyncio
    async def test_deep_mode_produces_results(self):
        """In 'deep' mode, execute stage returns one result per batch."""
        wf = TestAuditWorkflow(mode="deep")
        batches = [
            {
                "batch_id": "batch_0",
                "subsystem": "src/attune/foo",
                "modules": ["src/attune/foo/bar.py"],
                "task_xml": "<task/>",
            },
            {
                "batch_id": "batch_1",
                "subsystem": "src/attune/baz",
                "modules": ["src/attune/baz/qux.py"],
                "task_xml": "<task/>",
            },
        ]
        result, _, _ = await wf._execute_stage({"batches": batches}, ModelTier.CAPABLE)
        assert len(result["results"]) == 2
        assert result["batches_processed"] == 2

    @pytest.mark.asyncio
    async def test_deep_mode_result_has_status(self):
        """Deep-mode batch results have a 'status' key set to 'planned'."""
        wf = TestAuditWorkflow(mode="deep")
        batches = [
            {
                "batch_id": "batch_0",
                "subsystem": "src/attune/foo",
                "modules": [],
                "task_xml": "<task/>",
            }
        ]
        result, _, _ = await wf._execute_stage({"batches": batches}, ModelTier.CAPABLE)
        assert result["results"][0]["status"] == "planned"

    @pytest.mark.asyncio
    async def test_deep_mode_empty_batches(self):
        """Deep mode with no batches returns empty results."""
        wf = TestAuditWorkflow(mode="deep")
        result, _, _ = await wf._execute_stage({"batches": []}, ModelTier.CAPABLE)
        assert result["results"] == []
        assert result["batches_processed"] == 0

    @pytest.mark.asyncio
    async def test_execute_merges_input_data(self):
        """Execute output includes all keys from input_data."""
        wf = TestAuditWorkflow(mode="quick")
        result, _, _ = await wf._execute_stage(
            {"batches": [], "sentinel_key": "hello"},
            ModelTier.CAPABLE,
        )
        assert result.get("sentinel_key") == "hello"


# ---------------------------------------------------------------------------
# TestVerifyStage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVerifyStage:
    """Tests for the _verify stage."""

    @pytest.mark.asyncio
    async def test_verify_returns_tuple(self):
        """Verify stage returns a (dict, int, int) tuple."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "42 passed"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, in_tok, out_tok = await wf._verify({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert isinstance(result, dict)
        assert isinstance(in_tok, int)
        assert isinstance(out_tok, int)

    @pytest.mark.asyncio
    async def test_verify_calculates_delta(self):
        """Verify stage computes delta = coverage_after - coverage_before."""
        wf = TestAuditWorkflow()
        wf._coverage_before = 70.0

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules_after = [
            ModuleCoverage(
                path="src/attune/foo.py",
                stmts=100,
                covered=80,
                missing_lines=[],
                pct=80.0,
                priority=20.0,
            )
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules_after,
            ),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert result["before"] == pytest.approx(70.0)
        assert result["after"] == pytest.approx(80.0)
        assert result["delta"] == pytest.approx(10.0)

    @pytest.mark.asyncio
    async def test_verify_delta_is_none_when_before_missing(self):
        """Delta is None when coverage_before is unavailable."""
        wf = TestAuditWorkflow()
        # _coverage_before is None by default

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert result["delta"] is None

    @pytest.mark.asyncio
    async def test_verify_regressions_on_bad_exit(self):
        """Exit code 2+ sets regressions=1."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert result["regressions"] == 1

    @pytest.mark.asyncio
    async def test_verify_no_regressions_on_success(self):
        """Exit code 0 sets regressions=0."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert result["regressions"] == 0

    @pytest.mark.asyncio
    async def test_verify_parses_passed_count(self):
        """Verify stage parses the number of passed tests from pytest output."""
        wf = TestAuditWorkflow()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "200 passed, 3 warnings in 12.34s"
        mock_result.stderr = ""

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert result["tests_total"] == 200

    @pytest.mark.asyncio
    async def test_verify_handles_subprocess_error_gracefully(self):
        """Subprocess failure during verify does not raise; result keys still present."""
        wf = TestAuditWorkflow()

        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("failed"),
        ):
            result, _, _ = await wf._verify({}, ModelTier.CHEAP)

        assert "before" in result
        assert "after" in result
        assert "delta" in result

    @pytest.mark.asyncio
    async def test_verify_uses_coverage_before_from_input(self):
        """Verify prefers coverage_before from input_data over _coverage_before."""
        wf = TestAuditWorkflow()
        wf._coverage_before = 50.0  # Should be overridden by input

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        modules_after = [
            ModuleCoverage(
                path="src/attune/bar.py",
                stmts=100,
                covered=60,
                missing_lines=[],
                pct=60.0,
                priority=40.0,
            )
        ]

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=modules_after,
            ),
        ):
            result, _, _ = await wf._verify({"coverage_before": 55.0}, ModelTier.CHEAP)

        assert result["before"] == pytest.approx(55.0)
        assert result["delta"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModuleSerialisation:
    """Tests for _module_to_dict and _dict_to_module round-trip."""

    def test_module_to_dict_roundtrip(self):
        """_module_to_dict followed by _dict_to_module reconstructs the object."""
        original = _make_module(
            path="src/attune/utils.py",
            stmts=50,
            covered=25,
            missing_lines=[1, 2, 3],
            pct=50.0,
            priority=25.0,
        )
        as_dict = _module_to_dict(original)
        restored = _dict_to_module(as_dict)
        assert restored.path == original.path
        assert restored.stmts == original.stmts
        assert restored.covered == original.covered
        assert restored.missing_lines == original.missing_lines
        assert restored.pct == pytest.approx(original.pct)
        assert restored.priority == pytest.approx(original.priority)

    def test_dict_to_module_defaults_on_missing_keys(self):
        """_dict_to_module handles an empty dict without raising."""
        module = _dict_to_module({})
        assert module.path == ""
        assert module.stmts == 0
        assert module.covered == 0
        assert module.missing_lines == []
        assert module.pct == pytest.approx(0.0)
        assert module.priority == pytest.approx(0.0)


@pytest.mark.unit
class TestSummarizeMissing:
    """Tests for the _summarize_missing helper."""

    def test_empty_list(self):
        """Empty module list produces an empty string."""
        assert _summarize_missing([]) == ""

    def test_single_module(self):
        """Single module appears in the summary."""
        m = _make_module(path="src/attune/alpha.py", missing_lines=[1, 2, 3])
        summary = _summarize_missing([m])
        assert "alpha.py" in summary
        assert "3 lines" in summary

    def test_more_than_five_modules(self):
        """Six or more modules show the first five plus a '+N more' suffix."""
        modules = [_make_module(path=f"src/attune/mod{i}.py", missing_lines=[1]) for i in range(6)]
        summary = _summarize_missing(modules)
        assert "+1 more" in summary

    def test_five_modules_no_more_suffix(self):
        """Exactly five modules have no '+N more' suffix."""
        modules = [_make_module(path=f"src/attune/mod{i}.py", missing_lines=[]) for i in range(5)]
        summary = _summarize_missing(modules)
        assert "more" not in summary


@pytest.mark.unit
class TestBuildBatchResult:
    """Tests for _build_batch_result."""

    def test_status_is_planned(self):
        """Batch result always has status='planned'."""
        batch = {
            "batch_id": "batch_0",
            "subsystem": "src/attune/foo",
            "task_xml": "<task/>",
        }
        result = _build_batch_result(batch)
        assert result["status"] == "planned"

    def test_tests_added_is_zero(self):
        """tests_added defaults to 0 (generation is deferred to agent)."""
        batch = {"batch_id": "batch_0", "subsystem": "x", "task_xml": ""}
        result = _build_batch_result(batch)
        assert result["tests_added"] == 0

    def test_files_created_is_empty_list(self):
        """files_created defaults to empty list."""
        batch = {"batch_id": "batch_0", "subsystem": "x", "task_xml": ""}
        result = _build_batch_result(batch)
        assert result["files_created"] == []

    def test_preserves_batch_id(self):
        """Batch result preserves batch_id from the input batch."""
        batch = {"batch_id": "batch_42", "subsystem": "x", "task_xml": ""}
        result = _build_batch_result(batch)
        assert result["batch_id"] == "batch_42"

    def test_preserves_task_xml(self):
        """Batch result preserves task_xml from the input batch."""
        xml = "<task id='1'><objective>test</objective></task>"
        batch = {"batch_id": "batch_0", "subsystem": "x", "task_xml": xml}
        result = _build_batch_result(batch)
        assert result["task_xml"] == xml
