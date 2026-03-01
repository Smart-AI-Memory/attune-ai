"""Tests for WorkflowAgentAdapter.

Tests that BaseWorkflow subclasses can be wrapped as agents
for DynamicTeam composition.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from attune.agents.sdk.sdk_models import SDKAgentResult
from attune.cost_tracker import CostTracker
from attune.orchestration.workflow_agent_adapter import WorkflowAgentAdapter
from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier

# ---------------------------------------------------------------------------
# Stub workflows
# ---------------------------------------------------------------------------


class _SuccessWorkflow(BaseWorkflow):
    """Workflow that always succeeds."""

    name = "success-workflow"
    description = "Always succeeds"
    stages = ["stage_a", "stage_b"]
    tier_map = {
        "stage_a": ModelTier.CHEAP,
        "stage_b": ModelTier.CAPABLE,
    }

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        return {"stage": stage_name, "result": "ok"}, 100, 50


class _FailingWorkflow(BaseWorkflow):
    """Workflow that always fails."""

    name = "failing-workflow"
    description = "Always fails"
    stages = ["stage_a"]
    tier_map = {"stage_a": ModelTier.CHEAP}

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        raise ValueError("Intentional failure")


# ---------------------------------------------------------------------------
# Tests: WorkflowAgentAdapter
# ---------------------------------------------------------------------------


class TestWorkflowAgentAdapter:
    """Tests for wrapping workflows as agents."""

    @pytest.fixture
    def cost_tracker(self, tmp_path: Path) -> CostTracker:
        return CostTracker(storage_dir=str(tmp_path / ".empathy"))

    def test_wraps_workflow_as_agent(self, cost_tracker: CostTracker) -> None:
        """process() returns SDKAgentResult from workflow execution."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
        )

        result = adapter.process({"data": "test"})

        assert isinstance(result, SDKAgentResult)
        assert result.success is True
        assert result.role == "success-workflow"
        assert result.execution_time_ms > 0

    def test_converts_result_findings(self, cost_tracker: CostTracker) -> None:
        """Findings include workflow metadata."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
        )

        result = adapter.process({"data": "test"})

        assert result.findings["workflow_name"] == "success-workflow"
        assert result.findings["success"] is True
        assert result.findings["stage_count"] == 2
        assert "stages" in result.findings

    def test_score_for_successful_workflow(self, cost_tracker: CostTracker) -> None:
        """Successful workflow gets score >= 80."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
        )

        result = adapter.process({"data": "test"})

        assert result.score >= 80.0
        assert result.score <= 100.0

    def test_handles_workflow_failure(self, cost_tracker: CostTracker) -> None:
        """Failed workflow returns SDKAgentResult with success=False."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_FailingWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
        )

        result = adapter.process({"data": "test"})

        assert isinstance(result, SDKAgentResult)
        assert result.success is False
        assert result.score == 0.0

    def test_custom_agent_id_and_role(self, cost_tracker: CostTracker) -> None:
        """Custom agent_id and role are used."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
            agent_id="custom-id",
            role="Custom Role",
        )

        result = adapter.process({"data": "test"})

        assert result.agent_id == "custom-id"
        assert result.role == "Custom Role"

    def test_auto_generates_agent_id(self) -> None:
        """Agent ID is auto-generated when not provided."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
        )

        assert adapter.agent_id.startswith("wf-adapter-")

    def test_passes_state_store(self, tmp_path: Path) -> None:
        """state_store is forwarded to workflow constructor."""
        from attune.agents.state.store import AgentStateStore

        state_store = AgentStateStore(storage_dir=str(tmp_path / "state"))
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))

        adapter = WorkflowAgentAdapter(
            workflow_class=_SuccessWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
            state_store=state_store,
        )

        result = adapter.process({"data": "test"})

        assert result.success is True

    def test_failure_returns_error_message(self, cost_tracker: CostTracker) -> None:
        """Failed workflow includes error details."""
        adapter = WorkflowAgentAdapter(
            workflow_class=_FailingWorkflow,
            workflow_kwargs={"cost_tracker": cost_tracker},
        )

        result = adapter.process({"data": "test"})

        # The error could be in result.error or in findings
        has_error = result.error is not None or "error" in result.findings
        assert has_error
