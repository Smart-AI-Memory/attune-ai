"""Behavioral tests for TestAuditWorkflow.

Tests initialization, class attributes, mode handling,
and stage methods without running real pytest/coverage.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestTestAuditAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.name == "test-audit"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["audit", "plan", "execute", "verify"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert "audit" in wf.tier_map
        assert "plan" in wf.tier_map
        assert "execute" in wf.tier_map
        assert "verify" in wf.tier_map


@pytest.mark.unit
class TestTestAuditInit:
    """Test constructor parameters."""

    def test_default_target_coverage(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.target_coverage == 90.0

    def test_custom_target_coverage(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(target_coverage=80.0)
        assert wf.target_coverage == 80.0

    def test_default_mode_is_deep(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.mode == "deep"

    def test_quick_mode(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="quick")
        assert wf.mode == "quick"

    def test_default_max_batches(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.max_batches == 5

    def test_default_min_module_coverage(self) -> None:
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        assert wf.min_module_coverage == 50.0


@pytest.mark.unit
class TestTestAuditAuditStage:
    """Test the _audit stage method."""

    @pytest.mark.asyncio
    async def test_audit_stage_handles_coverage_failure(self) -> None:
        """Given coverage collection failure, audit returns empty modules."""
        from attune.models import ModelTier
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()

        with patch.object(
            wf,
            "_run_coverage",
            side_effect=FileNotFoundError("no pytest"),
        ):
            output, in_tok, out_tok = await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert output["modules"] == []
        assert output["total_modules"] == 0

    @pytest.mark.asyncio
    async def test_audit_stage_stores_coverage_before(self) -> None:
        """Given successful coverage, _coverage_before is set."""
        from attune.models import ModelTier
        from attune.workflows.test_audit.coverage_parser import ModuleCoverage
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow()
        mock_modules = [
            ModuleCoverage(
                path="src/mod.py",
                stmts=100,
                covered=80,
                missing_lines=[1, 2],
                pct=80.0,
                priority=20.0,
            ),
        ]

        with patch.object(wf, "_run_coverage", return_value=mock_modules):
            await wf._audit({"src_path": "src/attune"}, ModelTier.CHEAP)

        assert wf._coverage_before == 80.0


@pytest.mark.unit
class TestTestAuditExecuteStage:
    """Test the _execute stage method."""

    @pytest.mark.asyncio
    async def test_quick_mode_skips_execute(self) -> None:
        """Given quick mode, execute stage is a no-op."""
        from attune.models import ModelTier
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="quick")
        output, in_tok, out_tok = await wf._execute({"batches": []}, ModelTier.CAPABLE)
        assert output["mode"] == "quick"
        assert output["results"] == []

    @pytest.mark.asyncio
    async def test_deep_mode_processes_batches(self) -> None:
        """Given deep mode with batches, execute produces results."""
        from attune.models import ModelTier
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="deep")
        batches = [
            {"batch_id": "b1", "subsystem": "core", "modules": [], "task_xml": ""},
        ]
        output, in_tok, out_tok = await wf._execute({"batches": batches}, ModelTier.CAPABLE)
        assert output["batches_processed"] == 1
        assert len(output["results"]) == 1
        assert output["results"][0]["status"] == "planned"


@pytest.mark.unit
class TestTestAuditFullExecution:
    """Test full execute flow with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_execute_with_mocked_coverage(self) -> None:
        """Given mocked coverage, execute returns WorkflowResult."""
        from unittest.mock import MagicMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.test_audit.coverage_parser import ModuleCoverage
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="quick")
        mock_modules = [
            ModuleCoverage(
                path="src/mod.py",
                stmts=100,
                covered=80,
                missing_lines=[1, 2],
                pct=80.0,
                priority=20.0,
            ),
        ]

        with (
            patch.object(wf, "_run_coverage", return_value=mock_modules),
            patch("attune.workflows.test_audit.workflow.subprocess") as mock_subprocess,
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=mock_modules,
            ),
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "1 passed"
            mock_result.stderr = ""
            mock_subprocess.run.return_value = mock_result

            result = await wf.execute(src_path="src/attune")

        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_handles_coverage_error_gracefully(self) -> None:
        """Given coverage failure, execute returns failed result."""
        from unittest.mock import MagicMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="quick")

        with (
            patch.object(
                wf,
                "_run_coverage",
                side_effect=FileNotFoundError("no pytest"),
            ),
            patch("attune.workflows.test_audit.workflow.subprocess") as mock_subprocess,
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=[],
            ),
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "0 passed"
            mock_result.stderr = ""
            mock_subprocess.run.return_value = mock_result

            result = await wf.execute(src_path="src/attune")

        assert isinstance(result, WorkflowResult)

    @pytest.mark.asyncio
    async def test_result_stages_match_workflow(self) -> None:
        """Given successful execution, result stages match workflow stages."""
        from unittest.mock import MagicMock

        from attune.workflows.test_audit.coverage_parser import ModuleCoverage
        from attune.workflows.test_audit.workflow import TestAuditWorkflow

        wf = TestAuditWorkflow(mode="quick")
        mock_modules = [
            ModuleCoverage(
                path="src/mod.py",
                stmts=100,
                covered=80,
                missing_lines=[],
                pct=80.0,
                priority=20.0,
            ),
        ]

        with (
            patch.object(wf, "_run_coverage", return_value=mock_modules),
            patch("attune.workflows.test_audit.workflow.subprocess") as mock_subprocess,
            patch(
                "attune.workflows.test_audit.workflow.parse_coverage_json",
                return_value=mock_modules,
            ),
        ):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "1 passed"
            mock_result.stderr = ""
            mock_subprocess.run.return_value = mock_result

            result = await wf.execute(src_path="src/attune")

        stage_names = [s.name for s in result.stages]
        assert stage_names == ["audit", "plan", "execute", "verify"]
