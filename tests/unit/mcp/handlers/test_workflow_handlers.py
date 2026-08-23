"""Unit tests for workflow handler methods on EmpathyMCPServer.

Tests cover _run_security_audit, _run_bug_predict, _run_code_review,
_run_test_generation, _run_performance_audit, and _run_release_notes
via the server methods (previously tested via standalone functions in
the deleted attune.mcp.handlers.workflow_handlers module).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import EmpathyMCPServer


@pytest.fixture(autouse=True)
def _bypass_path_validation():
    """Skip path resolution so tests work on Windows too.

    _validate_file_path resolves paths via Path.resolve(), which on
    Windows turns "/code" into "D:\\code".  These tests verify handler
    logic, not path validation, so we stub it out.
    """

    def _passthrough(path, **_kwargs):
        return PurePosixPath(path)

    with patch(
        "attune.security.path_validation._validate_file_path",
        side_effect=_passthrough,
    ):
        yield


def _make_server(workspace_root: str = "/") -> EmpathyMCPServer:
    """Return a server instance with plugin/version-check init suppressed."""
    with patch.object(EmpathyMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return EmpathyMCPServer(workspace_root=workspace_root)


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
    """Tests for _run_security_audit()."""

    @pytest.mark.asyncio
    async def test_run_security_audit_returns_expected_keys(self):
        """Happy path: result dict has score, findings, cost, provider."""
        server = _make_server()
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
            out = await server._run_security_audit({"path": "/src"})

        assert out["success"] is True
        assert out["score"] == 85
        assert out["findings"] == ["issue-1"]
        assert out["cost"] == 0.05
        assert out["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_run_security_audit_empty_findings(self):
        """Missing findings key in final_output defaults to empty list."""
        server = _make_server()
        result = _make_result(success=True, final_output={"health_score": 90})
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            out = await server._run_security_audit({"path": "."})

        assert out["findings"] == []

    @pytest.mark.asyncio
    async def test_run_security_audit_passes_path_to_execute(self):
        """execute() is called with path kwarg from args."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            await server._run_security_audit({"path": "/some/path"})

        workflow_instance = mod.SecurityAuditWorkflow.return_value
        workflow_instance.execute.assert_awaited_once_with(path="/some/path")


class TestRunBugPredict:
    """Tests for _run_bug_predict()."""

    @pytest.mark.asyncio
    async def test_run_bug_predict_returns_expected_keys(self):
        """Happy path: returns predictions and cost."""
        server = _make_server()
        result = _make_result(
            success=True,
            final_output={"predictions": ["pred-a", "pred-b"]},
            total_cost=0.02,
        )
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictionWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            out = await server._run_bug_predict({"path": "/src"})

        assert out["success"] is True
        assert out["predictions"] == ["pred-a", "pred-b"]
        assert out["cost"] == 0.02

    @pytest.mark.asyncio
    async def test_run_bug_predict_empty_predictions_default(self):
        """Missing predictions key defaults to empty list."""
        server = _make_server()
        result = _make_result(success=False, final_output={})
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictionWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            out = await server._run_bug_predict({"path": "."})

        assert out["predictions"] == []

    @pytest.mark.asyncio
    async def test_run_bug_predict_passes_path(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictionWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            await server._run_bug_predict({"path": "/code"})

        mod.BugPredictionWorkflow.return_value.execute.assert_awaited_once_with(path="/code")


class TestRunCodeReview:
    """Tests for _run_code_review()."""

    @pytest.mark.asyncio
    async def test_run_code_review_returns_expected_keys(self):
        """Happy path: returns feedback, score, cost."""
        server = _make_server()
        result = _make_result(
            success=True,
            final_output={"feedback": "Looks good", "quality_score": 9},
            total_cost=0.03,
        )
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            out = await server._run_code_review({"path": "/module.py"})

        assert out["success"] is True
        assert out["feedback"] == "Looks good"
        assert out["score"] == 9
        assert out["cost"] == 0.03

    @pytest.mark.asyncio
    async def test_run_code_review_passes_target_path(self):
        """execute() is called with path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            await server._run_code_review({"path": "/mymod.py"})

        mod.CodeReviewWorkflow.return_value.execute.assert_awaited_once_with(path="/mymod.py")

    @pytest.mark.asyncio
    async def test_run_code_review_none_feedback(self):
        """Missing keys return None from .get()."""
        server = _make_server()
        result = _make_result(success=True, final_output={})
        mod = _make_workflow_module("attune.workflows.code_review", "CodeReviewWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.code_review": mod}):
            out = await server._run_code_review({"path": "."})

        assert out["feedback"] is None
        assert out["score"] is None


class TestRunTestGeneration:
    """Tests for _run_test_generation()."""

    @pytest.mark.asyncio
    async def test_run_test_generation_returns_expected_keys(self):
        """Happy path: returns tests_generated and output_path."""
        server = _make_server()
        result = _make_result(
            success=True,
            final_output={"tests_generated": 12, "output_path": "tests/test_mod.py"},
            total_cost=0.04,
        )
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            out = await server._run_test_generation({"module": "src/mymod.py"})

        assert out["success"] is True
        assert out["tests_generated"] == 12
        assert out["output_path"] == "tests/test_mod.py"
        assert out["cost"] == 0.04

    @pytest.mark.asyncio
    async def test_run_test_generation_passes_path(self):
        """execute() is called with the canonical `path` kwarg.

        The TOOL input key stays `module`; only the execute kwarg is
        fixed from the legacy `module_path` (which execute ignored, so
        every call failed with "path argument is required").
        """
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            await server._run_test_generation({"module": "src/foo.py"})

        mod.TestGenerationWorkflow.return_value.execute.assert_awaited_once_with(path="src/foo.py")

    @pytest.mark.asyncio
    async def test_run_test_generation_zero_tests_default(self):
        """tests_generated defaults to 0 when key absent from output."""
        server = _make_server()
        result = _make_result(success=False, final_output={})
        mod = _make_workflow_module("attune.workflows.test_gen", "TestGenerationWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_gen": mod}):
            out = await server._run_test_generation({"module": "m.py"})

        assert out["tests_generated"] == 0


class TestRunPerformanceAudit:
    """Tests for _run_performance_audit()."""

    @pytest.mark.asyncio
    async def test_run_performance_audit_returns_expected_keys(self):
        """Happy path: returns findings, score, cost."""
        server = _make_server()
        result = _make_result(
            success=True,
            final_output={"findings": ["slow-loop"], "score": 70},
            total_cost=0.06,
        )
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            out = await server._run_performance_audit({"path": "/src"})

        assert out["success"] is True
        assert out["findings"] == ["slow-loop"]
        assert out["score"] == 70
        assert out["cost"] == 0.06

    @pytest.mark.asyncio
    async def test_run_performance_audit_empty_findings_default(self):
        """Absent findings key defaults to empty list."""
        server = _make_server()
        result = _make_result(success=True, final_output={})
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            out = await server._run_performance_audit({"path": "."})

        assert out["findings"] == []

    @pytest.mark.asyncio
    async def test_run_performance_audit_passes_path(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.perf_audit", "PerformanceAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.perf_audit": mod}):
            await server._run_performance_audit({"path": "/app"})

        mod.PerformanceAuditWorkflow.return_value.execute.assert_awaited_once_with(path="/app")


class TestRunReleaseNotes:
    """Tests for _run_release_notes()."""

    @pytest.mark.asyncio
    async def test_run_release_notes_returns_expected_keys(self):
        """Happy path: returns approved, health_score, recommendation, cost."""
        server = _make_server()
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
            out = await server._run_release_notes({"path": "."})

        assert out["success"] is True
        assert out["approved"] is True
        assert out["health_score"] == 95
        assert out["recommendation"] == "Ship it"
        assert out["cost"] == 0.08

    @pytest.mark.asyncio
    async def test_run_release_notes_defaults_path_to_dot(self):
        """When path is not in args, defaults to '.'."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            out = await server._run_release_notes({})

        assert "success" in out

    @pytest.mark.asyncio
    async def test_run_release_notes_instantiates_without_args(self):
        """ReleasePreparationWorkflow is instantiated with no arguments."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            await server._run_release_notes({"path": "/proj"})

        mod.ReleasePreparationWorkflow.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_run_release_notes_passes_path_to_execute(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            await server._run_release_notes({"path": "/proj"})

        mod.ReleasePreparationWorkflow.return_value.execute.assert_awaited_once_with(path="/proj")

    @pytest.mark.asyncio
    async def test_run_release_notes_handles_string_final_output(self):
        """Regression: when ``final_output`` degrades to a plain string
        (workflow short-circuited with an error message), the handler
        must not AttributeError on ``.get()``. The string is surfaced as
        ``recommendation`` and the dict-shaped fields are ``None``."""
        server = _make_server()
        result = _make_result(
            success=False,
            final_output="Workflow short-circuited: missing API key",
            total_cost=0.0,
        )
        mod = _make_workflow_module(
            "attune.workflows.release_prep", "ReleasePreparationWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.release_prep": mod}):
            out = await server._run_release_notes({"path": "."})

        assert out["success"] is False
        assert out["approved"] is None
        assert out["health_score"] is None
        assert out["recommendation"] == "Workflow short-circuited: missing API key"
        assert out["cost"] == 0.0


class TestRunBugPredictReportFidelity:
    """The handler against what the workflow REALLY emits since #2193.

    The tests above feed a hand-made ``{"predictions": [...]}`` dict, which
    proves plumbing, not fidelity: ``BugPredictionWorkflow`` now returns a
    serialized ``WorkflowReport`` in ``final_output``. If the handler's
    ``predictions`` pick ever stopped resolving to the report's findings,
    the MCP tool would return ``[]`` while the CLI showed a full table —
    and every test here would stay green. Round table
    q-bug-predict-health-001 (2026-08-23), chair-promoted C4; zero cost.
    """

    @pytest.mark.asyncio
    async def test_serialized_report_findings_surface_as_predictions(self):
        from attune.workflows.output import Finding, FindingsSection, WorkflowReport

        report = WorkflowReport(
            title="Bug prediction",
            summary="risk concentrates in two boundary functions",
            score=66,
            sections=[
                FindingsSection(
                    title="Bugs",
                    tier="essential",
                    findings=[
                        Finding(
                            severity="high",
                            file="src/attune/agents/release/security_agent.py",
                            line=115,
                            message="ratchet lifts the -1 sentinel",
                        ),
                        Finding(severity="low", file="src/x.py", line=3, message="minor"),
                    ],
                )
            ],
        )
        result = _make_result(success=True, final_output=report.to_dict(), total_cost=1.17)
        mod = _make_workflow_module("attune.workflows.bug_predict", "BugPredictionWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.bug_predict": mod}):
            out = await server_with_root()._run_bug_predict({"path": "src"})

        assert out["success"] is True
        assert out["score"] == 66
        assert [p["severity"] for p in out["predictions"]] == ["high", "low"]
        assert out["predictions"][0]["file"].endswith("security_agent.py")
        assert out["predictions"][0]["line"] == 115
        assert "## Bugs" in out["summary_markdown"] or "Bugs" in out["summary_markdown"]


def server_with_root():
    """A server whose workspace root admits the relative ``src`` path."""
    return _make_server()
