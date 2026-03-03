"""Unit tests for attune.mcp.handlers.workflow_handlers."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_server() -> MagicMock:
    return MagicMock()


def _make_result(
    success: bool = True,
    final_output: dict | None = None,
    total_cost: float = 0.01,
    provider: str = "anthropic",
) -> MagicMock:
    """Build a fake WorkflowResult-like object."""
    result = MagicMock()
    result.success = success
    result.final_output = final_output or {}
    result.cost_report = MagicMock()
    result.cost_report.total_cost = total_cost
    result.provider = provider
    return result


def _make_workflow_module(module_name: str, class_name: str, result: MagicMock) -> ModuleType:
    """Build a fake workflow module with an async execute method."""
    mod = ModuleType(module_name)
    workflow_cls = MagicMock()
    workflow_instance = MagicMock()
    workflow_instance.execute = AsyncMock(return_value=result)
    workflow_cls.return_value = workflow_instance
    setattr(mod, class_name, workflow_cls)
    return mod


class TestRunSecurityAudit:
    """Tests for run_security_audit()."""

    @pytest.mark.asyncio
    async def test_run_security_audit_returns_expected_keys(self):
        """Happy path: result dict has score, findings, cost, provider."""
        from attune.mcp.handlers.workflow_handlers import run_security_audit

        result = _make_result(
            success=True,
            final_output={"health_score": 85, "findings": ["issue-1"]},
            total_cost=0.05,
            provider="anthropic",
        )
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            out = await run_security_audit(_make_server(), {"path": "/src"})

        assert out["success"] is True
        assert out["score"] == 85
        assert out["findings"] == ["issue-1"]
        assert out["cost"] == 0.05
        assert out["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_run_security_audit_empty_findings(self):
        """Missing findings key in final_output defaults to empty list."""
        from attune.mcp.handlers.workflow_handlers import run_security_audit

        result = _make_result(success=True, final_output={"health_score": 90})
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            out = await run_security_audit(_make_server(), {"path": "."})

        assert out["findings"] == []

    @pytest.mark.asyncio
    async def test_run_security_audit_passes_path_to_execute(self):
        """execute() is called with path kwarg from args."""
        from attune.mcp.handlers.workflow_handlers import run_security_audit

        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            await run_security_audit(_make_server(), {"path": "/some/path"})

        workflow_instance = mod.SecurityAuditWorkflow.return_value
        workflow_instance.execute.assert_awaited_once_with(path="/some/path")


class TestRunBugPredict:
    """Tests for run_bug_predict()."""

    @pytest.mark.asyncio
    async def test_run_bug_predict_returns_expected_keys(self):
        """Happy path: returns predictions and cost."""
        from attune.mcp.handlers.workflow_handlers import run_bug_predict

        result = _make_result(
            success=True,
            final_output={"predictions": ["pred-a", "pred-b"]},
            total_cost=0.02,
        )
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            out = await run_bug_predict(_make_server(), {"path": "/src"})

        assert out["success"] is True
        assert out["predictions"] == ["pred-a", "pred-b"]
        assert out["cost"] == 0.02

    @pytest.mark.asyncio
    async def test_run_bug_predict_empty_predictions_default(self):
        """Missing predictions key defaults to empty list."""
        from attune.mcp.handlers.workflow_handlers import run_bug_predict

        result = _make_result(success=False, final_output={})
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            out = await run_bug_predict(_make_server(), {"path": "."})

        assert out["predictions"] == []

    @pytest.mark.asyncio
    async def test_run_bug_predict_passes_path(self):
        """execute() receives path kwarg."""
        from attune.mcp.handlers.workflow_handlers import run_bug_predict

        result = _make_result()
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            await run_bug_predict(_make_server(), {"path": "/code"})

        mod.BugPredictWorkflow.return_value.execute.assert_awaited_once_with(path="/code")


class TestRunCodeReview:
    """Tests for run_code_review()."""

    @pytest.mark.asyncio
    async def test_run_code_review_returns_expected_keys(self):
        """Happy path: returns feedback, score, cost."""
        from attune.mcp.handlers.workflow_handlers import run_code_review

        result = _make_result(
            success=True,
            final_output={"feedback": "Looks good", "quality_score": 9},
            total_cost=0.03,
        )
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            out = await run_code_review(_make_server(), {"path": "/module.py"})

        assert out["success"] is True
        assert out["feedback"] == "Looks good"
        assert out["score"] == 9
        assert out["cost"] == 0.03

    @pytest.mark.asyncio
    async def test_run_code_review_passes_target_path(self):
        """execute() is called with target_path kwarg."""
        from attune.mcp.handlers.workflow_handlers import run_code_review

        result = _make_result()
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            await run_code_review(_make_server(), {"path": "/mymod.py"})

        mod.CodeReviewWorkflow.return_value.execute.assert_awaited_once_with(
            target_path="/mymod.py"
        )

    @pytest.mark.asyncio
    async def test_run_code_review_none_feedback(self):
        """Missing keys return None from .get()."""
        from attune.mcp.handlers.workflow_handlers import run_code_review

        result = _make_result(success=True, final_output={})
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            out = await run_code_review(_make_server(), {"path": "."})

        assert out["feedback"] is None
        assert out["score"] is None


class TestRunTestGeneration:
    """Tests for run_test_generation()."""

    @pytest.mark.asyncio
    async def test_run_test_generation_returns_expected_keys(self):
        """Happy path: returns tests_generated and output_path."""
        from attune.mcp.handlers.workflow_handlers import run_test_generation

        result = _make_result(
            success=True,
            final_output={"tests_generated": 12, "output_path": "tests/test_mod.py"},
            total_cost=0.04,
        )
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            out = await run_test_generation(_make_server(), {"module": "src/mymod.py"})

        assert out["success"] is True
        assert out["tests_generated"] == 12
        assert out["output_path"] == "tests/test_mod.py"
        assert out["cost"] == 0.04

    @pytest.mark.asyncio
    async def test_run_test_generation_passes_module_path(self):
        """execute() is called with module_path kwarg."""
        from attune.mcp.handlers.workflow_handlers import run_test_generation

        result = _make_result()
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            await run_test_generation(_make_server(), {"module": "src/foo.py"})

        mod.TestGenerationWorkflow.return_value.execute.assert_awaited_once_with(
            module_path="src/foo.py"
        )

    @pytest.mark.asyncio
    async def test_run_test_generation_zero_tests_default(self):
        """tests_generated defaults to 0 when key absent from output."""
        from attune.mcp.handlers.workflow_handlers import run_test_generation

        result = _make_result(success=False, final_output={})
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            out = await run_test_generation(_make_server(), {"module": "m.py"})

        assert out["tests_generated"] == 0


class TestRunPerformanceAudit:
    """Tests for run_performance_audit()."""

    @pytest.mark.asyncio
    async def test_run_performance_audit_returns_expected_keys(self):
        """Happy path: returns findings, score, cost."""
        from attune.mcp.handlers.workflow_handlers import run_performance_audit

        result = _make_result(
            success=True,
            final_output={"findings": ["slow-loop"], "score": 70},
            total_cost=0.06,
        )
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            out = await run_performance_audit(_make_server(), {"path": "/src"})

        assert out["success"] is True
        assert out["findings"] == ["slow-loop"]
        assert out["score"] == 70
        assert out["cost"] == 0.06

    @pytest.mark.asyncio
    async def test_run_performance_audit_empty_findings_default(self):
        """Absent findings key defaults to empty list."""
        from attune.mcp.handlers.workflow_handlers import run_performance_audit

        result = _make_result(success=True, final_output={})
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            out = await run_performance_audit(_make_server(), {"path": "."})

        assert out["findings"] == []

    @pytest.mark.asyncio
    async def test_run_performance_audit_passes_path(self):
        """execute() receives path kwarg."""
        from attune.mcp.handlers.workflow_handlers import run_performance_audit

        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            await run_performance_audit(_make_server(), {"path": "/app"})

        mod.PerformanceAuditWorkflow.return_value.execute.assert_awaited_once_with(path="/app")


class TestRunReleasePrep:
    """Tests for run_release_prep()."""

    @pytest.mark.asyncio
    async def test_run_release_prep_returns_expected_keys(self):
        """Happy path: returns approved, health_score, recommendation, cost."""
        from attune.mcp.handlers.workflow_handlers import run_release_prep

        result = _make_result(
            success=True,
            final_output={
                "approved": True,
                "health_score": 95,
                "recommendation": "Ship it",
            },
            total_cost=0.08,
        )
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            out = await run_release_prep(_make_server(), {"path": "."})

        assert out["success"] is True
        assert out["approved"] is True
        assert out["health_score"] == 95
        assert out["recommendation"] == "Ship it"
        assert out["cost"] == 0.08

    @pytest.mark.asyncio
    async def test_run_release_prep_defaults_path_to_dot(self):
        """When path is not in args, defaults to '.'."""
        from attune.mcp.handlers.workflow_handlers import run_release_prep

        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            out = await run_release_prep(_make_server(), {})

        # Should not raise — path defaults to "."
        assert "success" in out

    @pytest.mark.asyncio
    async def test_run_release_prep_instantiates_with_skip_approve(self):
        """ReleasePreparationWorkflow is instantiated with skip_approve_if_clean=True."""
        from attune.mcp.handlers.workflow_handlers import run_release_prep

        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            await run_release_prep(_make_server(), {"path": "/proj"})

        mod.ReleasePreparationWorkflow.assert_called_once_with(skip_approve_if_clean=True)

    @pytest.mark.asyncio
    async def test_run_release_prep_passes_path_to_execute(self):
        """execute() receives path kwarg."""
        from attune.mcp.handlers.workflow_handlers import run_release_prep

        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            await run_release_prep(_make_server(), {"path": "/proj"})

        mod.ReleasePreparationWorkflow.return_value.execute.assert_awaited_once_with(path="/proj")
