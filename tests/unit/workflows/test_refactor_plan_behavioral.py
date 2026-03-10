"""Behavioral tests for RefactorPlanWorkflow.

Tests initialization, class attributes, stage skipping,
scan stage, and analyze stage without hitting real LLMs.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestRefactorPlanAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.name == "refactor-plan"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["scan", "analyze", "prioritize", "plan"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert "scan" in wf.tier_map
        assert "analyze" in wf.tier_map
        assert "prioritize" in wf.tier_map
        assert "plan" in wf.tier_map


@pytest.mark.unit
class TestRefactorPlanInit:
    """Test constructor parameters."""

    def test_default_patterns_dir(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.patterns_dir == "./patterns"

    def test_default_min_debt_for_premium(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.min_debt_for_premium == 50

    def test_custom_min_debt_for_premium(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow(min_debt_for_premium=100)
        assert wf.min_debt_for_premium == 100

    def test_use_crew_default(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.use_crew_for_analysis is True


@pytest.mark.unit
class TestRefactorPlanStageSkipping:
    """Test should_skip_stage logic."""

    def test_plan_downgrades_when_low_debt(self) -> None:
        """Given low debt count, plan tier is downgraded to CAPABLE."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow(min_debt_for_premium=50)
        wf._total_debt = 10

        skip, reason = wf.should_skip_stage("plan", {})
        assert skip is False
        assert wf.tier_map["plan"] == ModelTier.CAPABLE

    def test_plan_not_skipped_when_high_debt(self) -> None:
        """Given high debt count, plan stage is not skipped."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow(min_debt_for_premium=50)
        wf._total_debt = 100

        skip, reason = wf.should_skip_stage("plan", {})
        assert skip is False

    def test_non_plan_stage_never_skipped(self) -> None:
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        skip, reason = wf.should_skip_stage("scan", {})
        assert skip is False


@pytest.mark.unit
class TestRefactorPlanScanStage:
    """Test the _scan stage method."""

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given empty directory, scan returns zero debt items."""
        from attune.models import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        output, in_tok, out_tok = await wf._scan({"path": str(tmp_path)}, ModelTier.CHEAP)
        assert output["total_debt"] == 0
        assert output["debt_items"] == []

    @pytest.mark.asyncio
    async def test_scan_finds_todo_markers(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a file with TODO, scan finds it."""
        from attune.models import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        test_file = tmp_path / "example.py"
        test_file.write_text("# TODO: fix this later\n")

        wf = RefactorPlanWorkflow()
        output, in_tok, out_tok = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]}, ModelTier.CHEAP
        )
        assert output["total_debt"] >= 1
        assert any(item["marker"] == "TODO" for item in output["debt_items"])

    @pytest.mark.asyncio
    async def test_scan_finds_fixme_markers(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a file with FIXME, scan finds it."""
        from attune.models import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        test_file = tmp_path / "example.py"
        test_file.write_text("# FIXME: broken thing\n")

        wf = RefactorPlanWorkflow()
        output, in_tok, out_tok = await wf._scan(
            {"path": str(tmp_path), "file_types": [".py"]}, ModelTier.CHEAP
        )
        assert output["total_debt"] >= 1
        assert any(item["marker"] == "FIXME" for item in output["debt_items"])


@pytest.mark.unit
class TestRefactorPlanAnalyzeStage:
    """Test the _analyze stage method."""

    @pytest.mark.asyncio
    async def test_analyze_stable_trajectory_without_history(self) -> None:
        """Given no debt history, trajectory is stable."""
        from attune.models import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        output, in_tok, out_tok = await wf._analyze(
            {"total_debt": 5, "by_file": {}}, ModelTier.CAPABLE
        )
        assert output["analysis"]["trajectory"] == "stable"

    @pytest.mark.asyncio
    async def test_analyze_returns_hotspots(self) -> None:
        """Given files with debt, analyze returns hotspots."""
        from attune.models import ModelTier
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        by_file = {"src/a.py": 5, "src/b.py": 3}
        output, in_tok, out_tok = await wf._analyze(
            {"total_debt": 8, "by_file": by_file}, ModelTier.CAPABLE
        )
        assert len(output["analysis"]["hotspots"]) == 2


@pytest.mark.unit
class TestRefactorPlanDefaultContext:
    """Test default_context class method."""

    def test_returns_workflow_context(self) -> None:
        from attune.workflows.context import WorkflowContext
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        ctx = RefactorPlanWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)


@pytest.mark.unit
class TestRefactorPlanExecution:
    """Test full execute flow with mocked LLM."""

    @pytest.mark.asyncio
    async def test_execute_with_mocked_llm(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a valid path and mocked LLM, execute returns WorkflowResult."""
        from unittest.mock import AsyncMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        # Create a file with a TODO so scan has something to find
        test_file = tmp_path / "example.py"
        test_file.write_text("# TODO: fix this\n")

        wf = RefactorPlanWorkflow()
        wf._call_llm = AsyncMock(return_value=("Phase 1: Fix high-priority items.", 50, 100))

        result = await wf.execute(path=str(tmp_path), file_types=[".py"])

        assert isinstance(result, WorkflowResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_handles_llm_error(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given LLM raising an error, execute returns failed result."""
        from unittest.mock import AsyncMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        test_file = tmp_path / "example.py"
        test_file.write_text("# TODO: fix this\n")

        wf = RefactorPlanWorkflow()
        wf._call_llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        result = await wf.execute(path=str(tmp_path), file_types=[".py"])

        assert isinstance(result, WorkflowResult)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_result_stages_match_workflow(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given successful execution, result stages match workflow stages."""
        from unittest.mock import AsyncMock

        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        test_file = tmp_path / "example.py"
        test_file.write_text("# TODO: fix this\n")

        wf = RefactorPlanWorkflow()
        wf._call_llm = AsyncMock(return_value=("Phase 1: Fix high-priority items.", 50, 100))

        result = await wf.execute(path=str(tmp_path), file_types=[".py"])

        stage_names = [s.name for s in result.stages]
        assert stage_names == ["scan", "analyze", "prioritize", "plan"]
