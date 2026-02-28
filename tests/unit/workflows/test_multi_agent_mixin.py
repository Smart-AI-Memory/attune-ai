"""Tests for MultiAgentStageMixin integration with BaseWorkflow.

Tests that workflow stages can delegate to DynamicTeam when
multi-agent configurations are provided.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.agents.sdk.sdk_models import SDKAgentResult
from attune.cost_tracker import CostTracker
from attune.orchestration.dynamic_team import DynamicTeamResult
from attune.workflows.base import BaseWorkflow
from attune.workflows.compat import ModelTier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_agent_result(
    agent_id: str = "agent-1",
    role: str = "Tester",
    score: float = 85.0,
    cost: float = 0.01,
) -> SDKAgentResult:
    """Create a mock SDKAgentResult."""
    return SDKAgentResult(
        agent_id=agent_id,
        role=role,
        success=True,
        score=score,
        cost=cost,
        findings={"score": score},
    )


def _make_team_result(
    agent_count: int = 2,
    success: bool = True,
    total_cost: float = 0.02,
) -> DynamicTeamResult:
    """Create a DynamicTeamResult for testing."""
    results = [
        _make_mock_agent_result(f"agent-{i}", f"Role-{i}", cost=total_cost / agent_count)
        for i in range(agent_count)
    ]
    return DynamicTeamResult(
        team_name="test-team",
        strategy="parallel",
        success=success,
        agent_results=results,
        quality_gate_results={},
        total_cost=total_cost,
        execution_time_ms=100.0,
    )


# ---------------------------------------------------------------------------
# Concrete workflow with multi-agent stage
# ---------------------------------------------------------------------------


class _MultiAgentWorkflow(BaseWorkflow):
    """Workflow that uses multi-agent stage for stage_b."""

    name = "multi-agent-test"
    description = "Tests multi-agent stage delegation"
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
        """Delegate stage_b to a multi-agent team."""
        if stage_name == "stage_b":
            return await self._run_multi_agent_stage(
                stage_name,
                input_data if isinstance(input_data, dict) else {"data": input_data},
            )
        return {"stage": stage_name, "result": "ok"}, 100, 50


# ---------------------------------------------------------------------------
# Tests: _run_multi_agent_stage
# ---------------------------------------------------------------------------


class TestMultiAgentStage:
    """Tests for the _run_multi_agent_stage method."""

    @pytest.fixture
    def cost_tracker(self, tmp_path: Path) -> CostTracker:
        """Create isolated CostTracker."""
        return CostTracker(storage_dir=str(tmp_path / ".empathy"))

    async def test_no_config_raises_value_error(self, cost_tracker: CostTracker) -> None:
        """Raises ValueError when no config is found."""
        wf = _MultiAgentWorkflow(cost_tracker=cost_tracker)

        with pytest.raises(ValueError, match="No multi-agent team config found"):
            await wf._run_multi_agent_stage("missing_stage", {})

    async def test_uses_stored_config(self, cost_tracker: CostTracker) -> None:
        """Looks up config from self._multi_agent_configs."""
        team_result = _make_team_result()

        with patch("attune.orchestration.team_builder.DynamicTeamBuilder") as MockBuilder:
            mock_team = MagicMock()
            mock_team.execute = AsyncMock(return_value=team_result)
            MockBuilder.return_value.build_from_plan.return_value = mock_team

            wf = _MultiAgentWorkflow(
                cost_tracker=cost_tracker,
                multi_agent_configs={
                    "stage_b": {
                        "agents": [{"template_id": "code_reviewer"}],
                        "strategy": "parallel",
                    },
                },
            )

            output, in_tokens, out_tokens = await wf._run_multi_agent_stage(
                "stage_b",
                {"data": "test"},
            )

            assert "team_success" in output
            MockBuilder.return_value.build_from_plan.assert_called_once()

    async def test_uses_provided_team_config(self, cost_tracker: CostTracker) -> None:
        """Uses team_config parameter over stored config."""
        team_result = _make_team_result()

        with patch("attune.orchestration.team_builder.DynamicTeamBuilder") as MockBuilder:
            mock_team = MagicMock()
            mock_team.execute = AsyncMock(return_value=team_result)
            MockBuilder.return_value.build_from_plan.return_value = mock_team

            wf = _MultiAgentWorkflow(cost_tracker=cost_tracker)

            output, _, _ = await wf._run_multi_agent_stage(
                "stage_b",
                {"data": "test"},
                team_config={
                    "agents": [{"template_id": "security_auditor"}],
                    "strategy": "sequential",
                },
            )

            assert output["strategy"] == "parallel"  # from DynamicTeamResult
            call_args = MockBuilder.return_value.build_from_plan.call_args[0][0]
            assert call_args["strategy"] == "sequential"

    async def test_returns_correct_tuple_format(self, cost_tracker: CostTracker) -> None:
        """Returns (dict, int, int) tuple."""
        team_result = _make_team_result(total_cost=0.03)

        with patch("attune.orchestration.team_builder.DynamicTeamBuilder") as MockBuilder:
            mock_team = MagicMock()
            mock_team.execute = AsyncMock(return_value=team_result)
            MockBuilder.return_value.build_from_plan.return_value = mock_team

            wf = _MultiAgentWorkflow(cost_tracker=cost_tracker)

            output, in_tokens, out_tokens = await wf._run_multi_agent_stage(
                "stage_b",
                {"data": "test"},
                team_config={"agents": [{"role": "Agent"}], "strategy": "parallel"},
            )

            assert isinstance(output, dict)
            assert isinstance(in_tokens, int)
            assert isinstance(out_tokens, int)
            assert in_tokens > 0  # Estimated from cost

    async def test_passes_state_store_to_builder(
        self,
        cost_tracker: CostTracker,
        tmp_path: Path,
    ) -> None:
        """state_store is forwarded to DynamicTeamBuilder."""
        from attune.agents.state.store import AgentStateStore

        state_store = AgentStateStore(storage_dir=str(tmp_path / "state"))
        team_result = _make_team_result()

        with patch("attune.orchestration.team_builder.DynamicTeamBuilder") as MockBuilder:
            mock_team = MagicMock()
            mock_team.execute = AsyncMock(return_value=team_result)
            MockBuilder.return_value.build_from_plan.return_value = mock_team

            wf = _MultiAgentWorkflow(cost_tracker=cost_tracker, state_store=state_store)

            await wf._run_multi_agent_stage(
                "stage_b",
                {"data": "test"},
                team_config={"agents": [{"role": "Agent"}], "strategy": "parallel"},
            )

            MockBuilder.assert_called_once_with(state_store=state_store)


# ---------------------------------------------------------------------------
# Tests: _merge_team_results
# ---------------------------------------------------------------------------


class TestMergeTeamResults:
    """Tests for the default _merge_team_results implementation."""

    def test_aggregates_agent_findings(self) -> None:
        """Output contains per-agent findings."""
        team_result = _make_team_result(agent_count=3)
        wf = _MultiAgentWorkflow.__new__(_MultiAgentWorkflow)

        merged = wf._merge_team_results(team_result, "test_stage")

        assert len(merged["agents"]) == 3
        for agent in merged["agents"]:
            assert "agent_id" in agent
            assert "role" in agent
            assert "findings" in agent

    def test_includes_quality_gates(self) -> None:
        """Output includes quality gate results."""
        team_result = _make_team_result()
        team_result.quality_gate_results = {"min_score": True}
        wf = _MultiAgentWorkflow.__new__(_MultiAgentWorkflow)

        merged = wf._merge_team_results(team_result, "test_stage")

        assert merged["quality_gate_results"] == {"min_score": True}

    def test_includes_metadata(self) -> None:
        """Output includes team name, strategy, cost, timing."""
        team_result = _make_team_result()
        wf = _MultiAgentWorkflow.__new__(_MultiAgentWorkflow)

        merged = wf._merge_team_results(team_result, "test_stage")

        assert merged["team_name"] == "test-team"
        assert merged["strategy"] == "parallel"
        assert merged["total_cost"] == 0.02
        assert "execution_time_ms" in merged


# ---------------------------------------------------------------------------
# Tests: _estimate_tokens_from_cost
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    """Tests for token estimation helper."""

    def test_zero_cost_returns_zero(self) -> None:
        """Zero cost gives zero tokens."""
        assert MultiAgentStageMixin._estimate_tokens_from_cost(0.0) == 0

    def test_negative_cost_returns_zero(self) -> None:
        """Negative cost gives zero tokens."""
        assert MultiAgentStageMixin._estimate_tokens_from_cost(-1.0) == 0

    def test_positive_cost_returns_tokens(self) -> None:
        """Positive cost returns estimated token count."""
        tokens = MultiAgentStageMixin._estimate_tokens_from_cost(0.003)
        assert tokens > 0
        assert isinstance(tokens, int)


# Import for direct testing of static method
from attune.workflows.multi_agent_mixin import MultiAgentStageMixin  # noqa: E402
