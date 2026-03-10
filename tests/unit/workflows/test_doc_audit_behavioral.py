"""Behavioral tests for DocAuditWorkflow.

Tests initialization, class attributes, stage methods, and
score computation without hitting real file systems or LLMs.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestDocAuditAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert wf.name == "doc-audit"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["audit", "plan", "execute", "verify"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert "audit" in wf.tier_map
        assert "plan" in wf.tier_map
        assert "execute" in wf.tier_map
        assert "verify" in wf.tier_map


@pytest.mark.unit
class TestDocAuditInit:
    """Test constructor parameters."""

    def test_default_auto_fix_enabled(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert wf.auto_fix is True

    def test_auto_fix_can_be_disabled(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(auto_fix=False)
        assert wf.auto_fix is False

    def test_default_project_root(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert wf.project_root == "."

    def test_custom_project_root(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(project_root="/tmp/test")
        assert wf.project_root == "/tmp/test"


@pytest.mark.unit
class TestDocAuditScoreComputation:
    """Test _compute_score helper."""

    def test_empty_results_returns_100(self) -> None:
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        assert wf._compute_score([]) == 100

    def test_all_pass_returns_100(self) -> None:
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
            CheckResult(id="c2", name="Check 2", status="pass", details="ok"),
        ]
        assert wf._compute_score(results) == 100

    def test_half_fail_returns_50(self) -> None:
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow()
        results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
            CheckResult(id="c2", name="Check 2", status="fail", details="bad"),
        ]
        assert wf._compute_score(results) == 50

    def test_strict_mode_counts_warn_as_fail(self) -> None:
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(strict=True)
        results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
            CheckResult(id="c2", name="Check 2", status="warn", details="meh"),
        ]
        assert wf._compute_score(results) == 50

    def test_non_strict_mode_counts_warn_as_pass(self) -> None:
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(strict=False)
        results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
            CheckResult(id="c2", name="Check 2", status="warn", details="meh"),
        ]
        assert wf._compute_score(results) == 100


@pytest.mark.unit
class TestDocAuditExecution:
    """Test execute flow with mocked stages."""

    @pytest.mark.asyncio
    async def test_execute_returns_workflow_result(self) -> None:
        """Given mocked checks, execute returns a WorkflowResult."""
        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(build_docs=False)

        mock_results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
        ]

        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=mock_results,
        ):
            result = await wf.execute(project_root=".")

        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_execute_handles_error_gracefully(self) -> None:
        """Given check failure, execute still returns a result."""
        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(build_docs=False)

        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            side_effect=RuntimeError("checks failed"),
        ):
            result = await wf.execute(project_root=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_result_stages_match_workflow(self) -> None:
        """Given successful execution, result stages match workflow stages."""
        from attune.workflows.doc_audit.checks import CheckResult
        from attune.workflows.doc_audit.workflow import DocAuditWorkflow

        wf = DocAuditWorkflow(build_docs=False)

        mock_results = [
            CheckResult(id="c1", name="Check 1", status="pass", details="ok"),
        ]

        with patch(
            "attune.workflows.doc_audit.workflow.run_all_checks",
            return_value=mock_results,
        ):
            result = await wf.execute(project_root=".")

        stage_names = [s.name for s in result.stages]
        assert stage_names == ["audit", "plan", "execute", "verify"]
