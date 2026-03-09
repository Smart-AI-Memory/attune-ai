"""Behavioral tests for PerformanceAuditWorkflow.

Tests initialization, class attributes, stage skipping logic,
and optimization action lookup.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestPerfAuditAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert wf.name == "perf-audit"

    def test_workflow_has_description(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert isinstance(wf.stages, list)
        assert wf.stages == ["profile", "analyze", "hotspots", "optimize"]

    def test_workflow_has_tier_map(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert "profile" in wf.tier_map
        assert "analyze" in wf.tier_map
        assert "hotspots" in wf.tier_map
        assert "optimize" in wf.tier_map

    def test_workflow_has_input_schema(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert wf.input_schema is not None
        assert "path" in wf.input_schema.required_fields


@pytest.mark.unit
class TestPerfAuditInit:
    """Test constructor parameters."""

    def test_default_min_hotspots(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert wf.min_hotspots_for_premium == 3

    def test_custom_min_hotspots(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow(min_hotspots_for_premium=10)
        assert wf.min_hotspots_for_premium == 10

    def test_default_auth_strategy_enabled(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        assert wf.enable_auth_strategy is True


@pytest.mark.unit
class TestPerfAuditStageSkipping:
    """Test should_skip_stage logic."""

    def test_optimize_downgrades_when_few_hotspots(self) -> None:
        """Given few hotspots, optimize tier is downgraded to CAPABLE."""
        from attune.workflows.compat import ModelTier
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow(min_hotspots_for_premium=3)
        wf._hotspot_count = 1

        skip, reason = wf.should_skip_stage("optimize", {})
        assert skip is False
        assert wf.tier_map["optimize"] == ModelTier.CAPABLE

    def test_optimize_not_skipped_when_many_hotspots(self) -> None:
        """Given many hotspots, optimize stage is not skipped."""
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow(min_hotspots_for_premium=3)
        wf._hotspot_count = 5

        skip, reason = wf.should_skip_stage("optimize", {})
        assert skip is False

    def test_non_optimize_stage_never_skipped(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        skip, reason = wf.should_skip_stage("profile", {})
        assert skip is False


@pytest.mark.unit
class TestPerfAuditOptimizationActions:
    """Test _get_optimization_action helper."""

    def test_known_concern_returns_action(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        # OPTIMIZATION_ACTIONS should have at least some entries
        from attune.workflows.perf_audit_patterns import OPTIMIZATION_ACTIONS

        if OPTIMIZATION_ACTIONS:
            first_key = next(iter(OPTIMIZATION_ACTIONS))
            result = wf._get_optimization_action(first_key)
            assert result is not None
            assert isinstance(result, dict)

    def test_unknown_concern_returns_none(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        result = wf._get_optimization_action("nonexistent_concern_xyz")
        assert result is None


@pytest.mark.unit
class TestPerfAuditDefaultContext:
    """Test default_context class method."""

    def test_returns_workflow_context(self) -> None:
        from attune.workflows.context import WorkflowContext
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        ctx = PerformanceAuditWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)

    def test_xml_disabled_by_default(self) -> None:
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        ctx = PerformanceAuditWorkflow.default_context()
        assert ctx.prompt is not None


@pytest.mark.unit
class TestPerfAuditExecution:
    """Test execute flow with mocked LLM."""

    @pytest.mark.asyncio
    async def test_execute_with_mocked_llm(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given a valid path and mocked LLM, execute returns WorkflowResult."""
        from unittest.mock import AsyncMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        wf._call_llm = AsyncMock(return_value=("No issues found.", 10, 20))

        result = await wf.execute(path=str(tmp_path))

        assert isinstance(result, WorkflowResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_handles_llm_error(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given LLM raising an error, execute returns failed result."""
        from unittest.mock import AsyncMock

        from attune.workflows.data_classes import WorkflowResult
        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        wf._call_llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        result = await wf.execute(path=str(tmp_path))

        assert isinstance(result, WorkflowResult)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_result_stages_match_workflow(self, tmp_path: pytest.TempPathFactory) -> None:
        """Given successful execution, result stages match workflow stages."""
        from unittest.mock import AsyncMock

        from attune.workflows.perf_audit import PerformanceAuditWorkflow

        wf = PerformanceAuditWorkflow()
        wf._call_llm = AsyncMock(return_value=("No issues found.", 10, 20))

        result = await wf.execute(path=str(tmp_path))

        stage_names = [s.name for s in result.stages]
        assert stage_names == ["profile", "analyze", "hotspots", "optimize"]
