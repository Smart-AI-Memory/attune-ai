"""Unit tests for WorkflowHandlersMixin path validation and handlers.

Tests cover _validated_path security enforcement and all 11 mixin
handlers: doc-audit, doc-gen, doc-orchestrator, test-audit,
test-gen-parallel, refactor-plan, dependency-check, simplify-code,
secure-release, health-check, and research-synthesis.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer

# ------------------------------------------------------------------
# Shared helpers (same pattern as test_workflow_handlers.py)
# ------------------------------------------------------------------


def _make_server(workspace_root: str = "/") -> AttuneMCPServer:
    """Return a server instance with plugin/version-check init suppressed."""
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return AttuneMCPServer(workspace_root=workspace_root)


def _make_result(
    success: bool = True,
    final_output: dict | None = None,
    total_cost: float = 0.01,
) -> MagicMock:
    """Build a fake WorkflowResult-like object."""
    result = MagicMock()
    result.success = success
    result.final_output = final_output or {}
    result.cost_report = MagicMock()
    result.cost_report.total_cost = total_cost
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


@pytest.fixture()
def _bypass_path_validation():
    """Stub out path validation so happy-path tests don't need real paths."""

    def _passthrough(path, **_kwargs):
        return PurePosixPath(path)

    with patch(
        "attune.security.path_validation._validate_file_path",
        side_effect=_passthrough,
    ):
        yield


# ==================================================================
# Security tests — do NOT use _bypass_path_validation
# ==================================================================


class TestMixinPathValidation:
    """Verify _validated_path calls _validate_file_path with allowed_dir."""

    @pytest.mark.asyncio
    async def test_doc_audit_validates_path(self):
        """_run_doc_audit passes path through _validate_file_path."""
        server = _make_server(workspace_root="/workspace")
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.doc_audit", "DocAuditWorkflow", result)

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=PurePosixPath("/workspace/src"),
            ) as mock_validate,
            patch.dict(sys.modules, {"attune.workflows.doc_audit": mod}),
        ):
            await server._run_doc_audit({"path": "src"})

        mock_validate.assert_called_once_with("src", allowed_dir="/workspace")

    @pytest.mark.asyncio
    async def test_doc_gen_validates_source_path(self):
        """_run_doc_gen validates source_path before reading."""
        server = _make_server(workspace_root="/workspace")
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.document_gen",
            "DocumentGenerationWorkflow",
            result,
        )

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=PurePosixPath("/workspace/src/mod.py"),
            ) as mock_validate,
            patch.dict(sys.modules, {"attune.workflows.document_gen": mod}),
            patch("pathlib.Path.read_text", return_value="code"),
        ):
            await server._run_doc_gen({"source_path": "src/mod.py"})

        mock_validate.assert_called_once_with("src/mod.py", allowed_dir="/workspace")

    @pytest.mark.asyncio
    async def test_refactor_plan_validates_path(self):
        """_run_refactor_plan passes path through _validate_file_path."""
        server = _make_server(workspace_root="/workspace")
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.refactor_plan", "RefactorPlanWorkflow", result
        )

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=PurePosixPath("/workspace/src"),
            ) as mock_validate,
            patch.dict(sys.modules, {"attune.workflows.refactor_plan": mod}),
        ):
            await server._run_refactor_plan({"path": "src"})

        mock_validate.assert_called_once_with("src", allowed_dir="/workspace")

    @pytest.mark.asyncio
    async def test_health_check_validates_project_root(self):
        """_run_health_check validates the project_root key."""
        server = _make_server(workspace_root="/workspace")
        result = _make_result()
        # health_check uses getattr on result, so mock attributes
        result.success = True
        result.overall_health_score = 90
        result.grade = "A"
        result.issues = []
        result.recommendations = []
        mod = _make_workflow_module(
            "attune.workflows.orchestrated_health_check",
            "OrchestratedHealthCheckWorkflow",
            result,
        )

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
                return_value=PurePosixPath("/workspace"),
            ) as mock_validate,
            patch.dict(
                sys.modules,
                {"attune.workflows.orchestrated_health_check": mod},
            ),
        ):
            await server._run_health_check({"project_root": "."})

        mock_validate.assert_called_once_with(".", allowed_dir="/workspace")

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        """Path traversal attempt raises ValueError."""
        server = _make_server(workspace_root="/workspace")

        with pytest.raises(ValueError):
            await server._run_doc_audit({"path": "../../etc/passwd"})

    @pytest.mark.asyncio
    async def test_doc_gen_validates_default_path_when_no_source_path(self):
        """_run_doc_gen validates the default path ('.') when source_path
        is absent — execute now takes a validated `path`, so the default
        is validated against the workspace root too."""
        server = _make_server(workspace_root="/workspace")
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.document_gen",
            "DocumentGenerationWorkflow",
            result,
        )

        with (
            patch(
                "attune.security.path_validation._validate_file_path",
            ) as mock_validate,
            patch.dict(sys.modules, {"attune.workflows.document_gen": mod}),
        ):
            await server._run_doc_gen({})

        mock_validate.assert_called_once_with(".", allowed_dir="/workspace")


# ==================================================================
# Happy-path tests — use _bypass_path_validation
# ==================================================================


class TestRunDocAudit:
    """Tests for _run_doc_audit()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns score, findings, cost."""
        server = _make_server()
        result = _make_result(
            final_output={"score": 88, "checks": ["md-001"]},
            total_cost=0.03,
        )
        mod = _make_workflow_module("attune.workflows.doc_audit", "DocAuditWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.doc_audit": mod}):
            out = await server._run_doc_audit({"path": "/src"})

        assert out["success"] is True
        assert out["score"] == 88
        assert out["findings"] == ["md-001"]
        assert out["cost"] == 0.03

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_defaults_path_to_dot(self):
        """Default path is '.' when key absent."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.doc_audit", "DocAuditWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.doc_audit": mod}):
            await server._run_doc_audit({})

        mod.DocAuditWorkflow.return_value.execute.assert_awaited_once_with(path=".")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_empty_checks_default(self):
        """Missing checks key defaults to empty list."""
        server = _make_server()
        result = _make_result(final_output={})
        mod = _make_workflow_module("attune.workflows.doc_audit", "DocAuditWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.doc_audit": mod}):
            out = await server._run_doc_audit({"path": "."})

        assert out["findings"] == []


class TestRunDocGen:
    """Tests for _run_doc_gen()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns document and sections."""
        server = _make_server()
        result = _make_result(
            final_output={"document": "# API", "sections": ["overview"]},
            total_cost=0.04,
        )
        mod = _make_workflow_module(
            "attune.workflows.document_gen",
            "DocumentGenerationWorkflow",
            result,
        )

        with (
            patch.dict(sys.modules, {"attune.workflows.document_gen": mod}),
            patch("pathlib.Path.read_text", return_value="def foo(): pass"),
        ):
            out = await server._run_doc_gen({"source_path": "src/mod.py"})

        assert out["success"] is True
        assert out["document"] == "# API"
        assert out["sections"] == ["overview"]

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_defaults_path_to_dot(self):
        """Absent source_path defaults the `path` kwarg to '.'."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.document_gen",
            "DocumentGenerationWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.document_gen": mod}):
            await server._run_doc_gen({})

        call_kwargs = mod.DocumentGenerationWorkflow.return_value.execute.call_args
        # execute reads `path` — NOT the legacy source_code/doc_type/audience
        # kwargs, which the SDK migration dropped. Guard against the drift
        # reappearing.
        assert call_kwargs.kwargs == {"path": "."}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_source_path_as_path(self):
        """The source_path arg is forwarded to execute() as `path`."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.document_gen",
            "DocumentGenerationWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.document_gen": mod}):
            await server._run_doc_gen({"source_path": "src/mod.py"})

        call_kwargs = mod.DocumentGenerationWorkflow.return_value.execute.call_args
        assert call_kwargs.kwargs == {"path": "src/mod.py"}
        assert "source_code" not in call_kwargs.kwargs
        assert "doc_type" not in call_kwargs.kwargs


class TestRunDocOrchestrator:
    """Tests for _run_doc_orchestrator()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns phase and items."""
        server = _make_server()
        result = MagicMock()
        result.phase = "complete"
        result.items_found = 5
        result.docs_generated = ["a.md"]
        result.docs_updated = ["b.md"]
        result.total_cost = 0.02
        mod = _make_workflow_module(
            "attune.workflows.documentation_orchestrator",
            "DocumentationOrchestrator",
            result,
        )

        with patch.dict(
            sys.modules,
            {"attune.workflows.documentation_orchestrator": mod},
        ):
            out = await server._run_doc_orchestrator({"path": "/src"})

        assert out["success"] is True
        assert out["phase"] == "complete"
        assert out["items_found"] == 5

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path(self):
        """Path is passed as the `path` kwarg (execute scopes off it)."""
        server = _make_server()
        result = MagicMock()
        result.phase = "complete"
        mod = _make_workflow_module(
            "attune.workflows.documentation_orchestrator",
            "DocumentationOrchestrator",
            result,
        )

        with patch.dict(
            sys.modules,
            {"attune.workflows.documentation_orchestrator": mod},
        ):
            await server._run_doc_orchestrator({"path": "/myproject"})

        call_kwargs = mod.DocumentationOrchestrator.return_value.execute.call_args
        # execute reads `path` (or the deprecated top-level `project_root`),
        # never a `context["project_root"]` — passing it inside context
        # silently dropped the scope.
        assert call_kwargs.kwargs == {"path": "/myproject"}


class TestRunTestAudit:
    """Tests for _run_test_audit()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns output and cost."""
        server = _make_server()
        result = _make_result(
            final_output={"coverage": 85},
            total_cost=0.05,
        )
        mod = _make_workflow_module("attune.workflows.test_audit", "TestAuditWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_audit": mod}):
            out = await server._run_test_audit({"path": "src/"})

        assert out["success"] is True
        assert out["output"] == {"coverage": 85}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_defaults_path_to_src(self):
        """Default path is 'src/' when key absent."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module("attune.workflows.test_audit", "TestAuditWorkflow", result)

        with patch.dict(sys.modules, {"attune.workflows.test_audit": mod}):
            await server._run_test_audit({})

        call_kwargs = mod.TestAuditWorkflow.return_value.execute.call_args
        # execute takes the canonical `path` kwarg now (`src_path` is a
        # deprecated alias). PurePosixPath strips trailing slash: "src/" → "src"
        assert call_kwargs.kwargs["path"] in ("src/", "src")
        assert "src_path" not in call_kwargs.kwargs


class TestRunTestGenParallel:
    """Tests for _run_test_gen_parallel() — no path validation needed."""

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self):
        """Happy path: returns completed count and files."""
        server = _make_server()
        result = _make_result(
            final_output={
                "total_modules": 10,
                "completed": 8,
                "errors": 2,
                "generated_files": ["test_a.py"],
            },
            total_cost=0.10,
        )
        mod = _make_workflow_module(
            "attune.workflows.test_gen_parallel",
            "ParallelTestGenerationWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.test_gen_parallel": mod}):
            out = await server._run_test_gen_parallel({"top": 50})

        assert out["success"] is True
        assert out["completed"] == 8
        assert out["errors"] == 2
        assert out["generated_files"] == ["test_a.py"]

    @pytest.mark.asyncio
    async def test_defaults(self):
        """Default top=200 and batch_size=10 when absent."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.test_gen_parallel",
            "ParallelTestGenerationWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.test_gen_parallel": mod}):
            await server._run_test_gen_parallel({})

        mod.ParallelTestGenerationWorkflow.return_value.execute.assert_awaited_once_with(
            top=200, batch_size=10
        )


class TestRunRefactorPlan:
    """Tests for _run_refactor_plan()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns output and cost."""
        server = _make_server()
        result = _make_result(
            final_output={"plan": "refactor X"},
            total_cost=0.03,
        )
        mod = _make_workflow_module(
            "attune.workflows.refactor_plan", "RefactorPlanWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.refactor_plan": mod}):
            out = await server._run_refactor_plan({"path": "/src"})

        assert out["success"] is True
        assert out["output"] == {"plan": "refactor X"}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path_to_execute(self):
        """execute() receives validated path."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.refactor_plan", "RefactorPlanWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.refactor_plan": mod}):
            await server._run_refactor_plan({"path": "/src"})

        mod.RefactorPlanWorkflow.return_value.execute.assert_awaited_once_with(path="/src")


class TestRunDependencyCheck:
    """Tests for _run_dependency_check()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns output and cost."""
        server = _make_server()
        result = _make_result(
            final_output={"vulnerabilities": []},
            total_cost=0.02,
        )
        mod = _make_workflow_module(
            "attune.workflows.dependency_check",
            "DependencyCheckWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.dependency_check": mod}):
            out = await server._run_dependency_check({"path": "."})

        assert out["success"] is True
        assert out["output"] == {"vulnerabilities": []}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.dependency_check",
            "DependencyCheckWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.dependency_check": mod}):
            await server._run_dependency_check({"path": "/proj"})

        mod.DependencyCheckWorkflow.return_value.execute.assert_awaited_once_with(path="/proj")


class TestRunSimplifyCode:
    """Tests for _run_simplify_code()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns output and cost."""
        server = _make_server()
        result = _make_result(
            final_output={"hotspots": 3},
            total_cost=0.04,
        )
        mod = _make_workflow_module(
            "attune.workflows.simplify_code",
            "SimplifyCodeWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.simplify_code": mod}):
            out = await server._run_simplify_code({"path": "/src"})

        assert out["success"] is True
        assert out["output"] == {"hotspots": 3}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = _make_result()
        mod = _make_workflow_module(
            "attune.workflows.simplify_code",
            "SimplifyCodeWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.simplify_code": mod}):
            await server._run_simplify_code({"path": "/app"})

        mod.SimplifyCodeWorkflow.return_value.execute.assert_awaited_once_with(path="/app")


class TestRunSecureRelease:
    """Tests for _run_secure_release()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns go/no-go and blockers."""
        server = _make_server()
        result = MagicMock()
        result.success = True
        result.go_no_go = "go"
        result.combined_risk_score = 15
        result.blockers = []
        result.warnings = ["low coverage"]
        result.total_cost = 0.07
        mod = _make_workflow_module(
            "attune.workflows.secure_release",
            "SecureReleasePipeline",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.secure_release": mod}):
            out = await server._run_secure_release({"path": "."})

        assert out["success"] is True
        assert out["go_no_go"] == "go"
        assert out["blockers"] == []
        assert out["warnings"] == ["low coverage"]

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path(self):
        """execute() receives path kwarg."""
        server = _make_server()
        result = MagicMock()
        mod = _make_workflow_module(
            "attune.workflows.secure_release",
            "SecureReleasePipeline",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.secure_release": mod}):
            await server._run_secure_release({"path": "/proj"})

        mod.SecureReleasePipeline.return_value.execute.assert_awaited_once_with(path="/proj")


class TestRunHealthCheck:
    """Tests for _run_health_check()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_returns_expected_keys(self):
        """Happy path: returns health score and grade."""
        server = _make_server()
        result = MagicMock()
        result.success = True
        result.overall_health_score = 92
        result.grade = "A"
        result.issues = []
        result.recommendations = ["add tests"]
        mod = _make_workflow_module(
            "attune.workflows.orchestrated_health_check",
            "OrchestratedHealthCheckWorkflow",
            result,
        )

        with patch.dict(
            sys.modules,
            {"attune.workflows.orchestrated_health_check": mod},
        ):
            out = await server._run_health_check({"project_root": "."})

        assert out["success"] is True
        assert out["health_score"] == 92
        assert out["grade"] == "A"
        assert out["recommendations"] == ["add tests"]

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_passes_path(self):
        """execute() receives the canonical `path` kwarg."""
        server = _make_server()
        result = MagicMock()
        mod = _make_workflow_module(
            "attune.workflows.orchestrated_health_check",
            "OrchestratedHealthCheckWorkflow",
            result,
        )

        with patch.dict(
            sys.modules,
            {"attune.workflows.orchestrated_health_check": mod},
        ):
            # The TOOL input key stays `project_root`; only the execute kwarg
            # is modernized to `path` (`project_root` is a deprecated alias).
            await server._run_health_check({"project_root": "/proj"})

        mod.OrchestratedHealthCheckWorkflow.return_value.execute.assert_awaited_once_with(
            path="/proj"
        )


class TestRunResearchSynthesis:
    """Tests for _run_research_synthesis() — path-driven workflow."""

    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, _bypass_path_validation):
        """Happy path: returns answer and insights."""
        server = _make_server()
        result = _make_result(
            final_output={
                "answer": "synthesis result",
                "key_insights": ["insight-1"],
                "confidence": 0.9,
            },
            total_cost=0.05,
        )
        mod = _make_workflow_module(
            "attune.workflows.research_synthesis",
            "ResearchSynthesisWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.research_synthesis": mod}):
            out = await server._run_research_synthesis({"path": "docs", "depth": "quick"})

        assert out["success"] is True
        assert out["answer"] == "synthesis result"
        assert out["key_insights"] == ["insight-1"]

    @pytest.mark.asyncio
    async def test_passes_path_and_depth_to_execute(self, _bypass_path_validation):
        """execute() receives validated path + depth (regression for the
        sources/question kwarg drift that left path empty)."""
        server = _make_server()
        result = _make_result(final_output={"answer": "ok"})
        mod = _make_workflow_module(
            "attune.workflows.research_synthesis",
            "ResearchSynthesisWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.research_synthesis": mod}):
            await server._run_research_synthesis({"path": "research", "depth": "deep"})

        mod.ResearchSynthesisWorkflow.return_value.execute.assert_awaited_once_with(
            path="research", depth="deep"
        )

    @pytest.mark.asyncio
    async def test_depth_defaults_to_standard(self, _bypass_path_validation):
        """Omitted depth defaults to 'standard'; omitted path defaults to '.'."""
        server = _make_server()
        result = _make_result(final_output={"answer": "ok"})
        mod = _make_workflow_module(
            "attune.workflows.research_synthesis",
            "ResearchSynthesisWorkflow",
            result,
        )

        with patch.dict(sys.modules, {"attune.workflows.research_synthesis": mod}):
            await server._run_research_synthesis({})

        mod.ResearchSynthesisWorkflow.return_value.execute.assert_awaited_once_with(
            path=".", depth="standard"
        )
