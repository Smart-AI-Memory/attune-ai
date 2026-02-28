"""Tests for WorkflowComposer.

Tests that multiple BaseWorkflow subclasses can be composed
into a DynamicTeam for parallel/sequential execution.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from attune.cost_tracker import CostTracker
from attune.orchestration.dynamic_team import DynamicTeam
from attune.orchestration.workflow_agent_adapter import WorkflowAgentAdapter
from attune.orchestration.workflow_composer import WorkflowComposer
from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier

# ---------------------------------------------------------------------------
# Stub workflows
# ---------------------------------------------------------------------------


class _SecurityWorkflow(BaseWorkflow):
    """Stub security audit workflow."""

    name = "security-audit"
    description = "Security audit stub"
    stages = ["scan"]
    tier_map = {"scan": ModelTier.CAPABLE}

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        return {"vulnerabilities": 0}, 100, 50


class _CodeReviewWorkflow(BaseWorkflow):
    """Stub code review workflow."""

    name = "code-review"
    description = "Code review stub"
    stages = ["review"]
    tier_map = {"review": ModelTier.CAPABLE}

    async def run_stage(
        self,
        stage_name: str,
        tier: ModelTier,
        input_data: Any,
    ) -> tuple[Any, int, int]:
        return {"issues": []}, 100, 50


# ---------------------------------------------------------------------------
# Tests: WorkflowComposer
# ---------------------------------------------------------------------------


class TestWorkflowComposer:
    """Tests for composing workflows into DynamicTeam."""

    @pytest.fixture
    def cost_tracker(self, tmp_path: Path) -> CostTracker:
        return CostTracker(storage_dir=str(tmp_path / ".empathy"))

    def test_compose_creates_dynamic_team(self, cost_tracker: CostTracker) -> None:
        """compose() returns a DynamicTeam instance."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="test-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
                {
                    "workflow": _CodeReviewWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
        )

        assert isinstance(team, DynamicTeam)
        assert team.team_name == "test-team"
        assert len(team.agents) == 2

    def test_agents_are_workflow_adapters(self, cost_tracker: CostTracker) -> None:
        """Composed agents are WorkflowAgentAdapter instances."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="test-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
        )

        assert isinstance(team.agents[0], WorkflowAgentAdapter)

    def test_compose_with_strategy(self, cost_tracker: CostTracker) -> None:
        """Strategy is forwarded to DynamicTeam."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="seq-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
            strategy="sequential",
        )

        assert team.strategy == "sequential"

    def test_compose_with_quality_gates(self, cost_tracker: CostTracker) -> None:
        """Quality gates are built and forwarded to DynamicTeam."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="gated-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
            quality_gates={"min_score": 70},
        )

        assert len(team.quality_gates) == 1
        assert team.quality_gates[0].name == "min_score"
        assert team.quality_gates[0].threshold == 70.0

    def test_compose_with_detailed_quality_gates(self, cost_tracker: CostTracker) -> None:
        """Detailed quality gate format is supported."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="gated-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
            quality_gates={
                "security_check": {
                    "agent_role": "security-audit",
                    "metric": "score",
                    "threshold": 80.0,
                    "required": True,
                },
            },
        )

        assert len(team.quality_gates) == 1
        gate = team.quality_gates[0]
        assert gate.name == "security_check"
        assert gate.agent_role == "security-audit"
        assert gate.threshold == 80.0

    def test_compose_empty_raises_value_error(self) -> None:
        """Empty workflows list raises ValueError."""
        composer = WorkflowComposer()

        with pytest.raises(ValueError, match="At least one workflow"):
            composer.compose(team_name="empty", workflows=[])

    def test_compose_with_custom_roles(self, cost_tracker: CostTracker) -> None:
        """Custom roles are forwarded to adapters."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="role-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                    "role": "Security Expert",
                },
                {
                    "workflow": _CodeReviewWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                    "role": "Code Reviewer",
                },
            ],
        )

        roles = [a.role for a in team.agents]
        assert "Security Expert" in roles
        assert "Code Reviewer" in roles

    def test_compose_passes_state_store(self, tmp_path: Path) -> None:
        """Composer's state_store is forwarded to all adapters."""
        from attune.agents.state.store import AgentStateStore

        state_store = AgentStateStore(storage_dir=str(tmp_path / "state"))
        cost_tracker = CostTracker(storage_dir=str(tmp_path / ".empathy"))

        composer = WorkflowComposer(state_store=state_store)

        team = composer.compose(
            team_name="state-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
        )

        adapter = team.agents[0]
        assert isinstance(adapter, WorkflowAgentAdapter)
        assert adapter.state_store is state_store

    def test_compose_with_phases(self, cost_tracker: CostTracker) -> None:
        """Phases are forwarded to DynamicTeam for two_phase strategy."""
        composer = WorkflowComposer()

        phases = [
            {"agent_indices": [0], "name": "gather"},
            {"agent_indices": [1], "name": "reason"},
        ]

        team = composer.compose(
            team_name="phased-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
                {
                    "workflow": _CodeReviewWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
            strategy="two_phase",
            phases=phases,
        )

        assert team.strategy == "two_phase"
        assert len(team.phases) == 2

    async def test_composed_team_execution(self, cost_tracker: CostTracker) -> None:
        """Composed team can be executed end-to-end."""
        composer = WorkflowComposer()

        team = composer.compose(
            team_name="e2e-team",
            workflows=[
                {
                    "workflow": _SecurityWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
                {
                    "workflow": _CodeReviewWorkflow,
                    "kwargs": {"cost_tracker": cost_tracker},
                },
            ],
            strategy="sequential",
        )

        result = await team.execute({"target": "src/"})

        assert result.team_name == "e2e-team"
        assert result.strategy == "sequential"
        assert len(result.agent_results) == 2
        assert all(r.success for r in result.agent_results)
