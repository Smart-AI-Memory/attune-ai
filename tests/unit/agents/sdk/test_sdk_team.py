"""Tests for SDKAgentTeam.

Tests parallel/sequential execution, quality gate evaluation,
and team result aggregation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any

import pytest

from attune.agents.sdk.sdk_agent import SDKAgent
from attune.agents.sdk.sdk_models import SDKAgentResult
from attune.agents.sdk.sdk_team import QualityGate, SDKAgentTeam, SDKTeamResult


def _make_mock_agent(
    role: str,
    success: bool = True,
    score: float = 90.0,
    confidence: float = 0.9,
    cost: float = 0.01,
) -> SDKAgent:
    """Create an SDKAgent with a mocked _execute_tier.

    Args:
        role: Agent role name.
        success: Whether execution should succeed.
        score: Score to return in findings.
        confidence: Confidence to return in findings.
        cost: Cost to report.

    Returns:
        SDKAgent with mocked execution.
    """
    agent = SDKAgent(role=role)

    def mock_execute(input_data: dict, tier: Any) -> tuple[bool, dict]:
        agent.total_cost = cost
        return success, {
            "score": score,
            "confidence": confidence,
            "mode": "mock",
        }

    agent._execute_tier = mock_execute  # type: ignore[assignment]
    return agent


class TestSDKAgentTeamExecution:
    """Tests for team execution strategies."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self) -> None:
        """Test that agents run in parallel."""
        agents = [
            _make_mock_agent("Auditor", score=90.0),
            _make_mock_agent("Tester", score=85.0),
            _make_mock_agent("Reviewer", score=92.0),
        ]
        team = SDKAgentTeam(
            team_name="Parallel Team",
            agents=agents,
            parallel=True,
        )
        result = await team.execute({"query": "test"})

        assert isinstance(result, SDKTeamResult)
        assert result.team_name == "Parallel Team"
        assert len(result.agent_results) == 3
        assert result.success is True
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_sequential_execution(self) -> None:
        """Test that agents run sequentially."""
        agents = [
            _make_mock_agent("Step1", score=80.0),
            _make_mock_agent("Step2", score=85.0),
        ]
        team = SDKAgentTeam(
            team_name="Sequential Team",
            agents=agents,
            parallel=False,
        )
        result = await team.execute({"query": "test"})

        assert len(result.agent_results) == 2
        assert result.success is True

    @pytest.mark.asyncio
    async def test_total_cost_aggregated(self) -> None:
        """Test that total cost is summed from all agents."""
        agents = [
            _make_mock_agent("A", cost=0.01),
            _make_mock_agent("B", cost=0.02),
            _make_mock_agent("C", cost=0.03),
        ]
        team = SDKAgentTeam(team_name="Cost Team", agents=agents)
        result = await team.execute({"query": "test"})

        assert abs(result.total_cost - 0.06) < 1e-9


class TestSDKAgentTeamQualityGates:
    """Tests for quality gate evaluation."""

    @pytest.mark.asyncio
    async def test_all_gates_pass(self) -> None:
        """Test success when all quality gates pass."""
        agents = [
            _make_mock_agent("Security", score=90.0),
            _make_mock_agent("Coverage", score=85.0),
        ]
        gates = [
            QualityGate(
                name="min_security",
                agent_role="Security",
                metric="score",
                threshold=80.0,
            ),
            QualityGate(
                name="min_coverage",
                agent_role="Coverage",
                metric="score",
                threshold=80.0,
            ),
        ]
        team = SDKAgentTeam(
            team_name="Gate Team",
            agents=agents,
            quality_gates=gates,
        )
        result = await team.execute({"query": "test"})

        assert result.success is True
        assert result.quality_gate_results["min_security"] is True
        assert result.quality_gate_results["min_coverage"] is True

    @pytest.mark.asyncio
    async def test_required_gate_fails(self) -> None:
        """Test failure when a required gate fails."""
        agents = [
            _make_mock_agent("Security", score=50.0),
            _make_mock_agent("Coverage", score=90.0),
        ]
        gates = [
            QualityGate(
                name="min_security",
                agent_role="Security",
                metric="score",
                threshold=80.0,
                required=True,
            ),
            QualityGate(
                name="min_coverage",
                agent_role="Coverage",
                metric="score",
                threshold=80.0,
                required=True,
            ),
        ]
        team = SDKAgentTeam(
            team_name="Failing Gate Team",
            agents=agents,
            quality_gates=gates,
        )
        result = await team.execute({"query": "test"})

        assert result.success is False
        assert result.quality_gate_results["min_security"] is False
        assert result.quality_gate_results["min_coverage"] is True

    @pytest.mark.asyncio
    async def test_optional_gate_failure_doesnt_fail_team(self) -> None:
        """Test that optional gate failure doesn't fail the team."""
        agents = [
            _make_mock_agent("Security", score=90.0),
            _make_mock_agent("Documentation", score=30.0),
        ]
        gates = [
            QualityGate(
                name="min_security",
                agent_role="Security",
                metric="score",
                threshold=80.0,
                required=True,
            ),
            QualityGate(
                name="min_docs",
                agent_role="Documentation",
                metric="score",
                threshold=80.0,
                required=False,
            ),
        ]
        team = SDKAgentTeam(
            team_name="Optional Gate Team",
            agents=agents,
            quality_gates=gates,
        )
        result = await team.execute({"query": "test"})

        assert result.success is True
        assert result.quality_gate_results["min_security"] is True
        assert result.quality_gate_results["min_docs"] is False

    @pytest.mark.asyncio
    async def test_gate_for_unknown_role_fails(self) -> None:
        """Test that gate referencing unknown role fails."""
        agents = [_make_mock_agent("Security", score=90.0)]
        gates = [
            QualityGate(
                name="min_phantom",
                agent_role="Phantom",
                metric="score",
                threshold=80.0,
                required=True,
            ),
        ]
        team = SDKAgentTeam(
            team_name="Missing Role Team",
            agents=agents,
            quality_gates=gates,
        )
        result = await team.execute({"query": "test"})

        assert result.success is False
        assert result.quality_gate_results["min_phantom"] is False

    @pytest.mark.asyncio
    async def test_no_quality_gates_defaults_to_success(self) -> None:
        """Test that team succeeds when no gates are defined."""
        agents = [_make_mock_agent("Solo", score=50.0)]
        team = SDKAgentTeam(
            team_name="No Gates Team",
            agents=agents,
            quality_gates=[],
        )
        result = await team.execute({"query": "test"})

        assert result.success is True


class TestSDKTeamResult:
    """Tests for SDKTeamResult serialization."""

    def test_to_dict(self) -> None:
        """Test SDKTeamResult serialization."""
        result = SDKTeamResult(
            team_name="Test Team",
            success=True,
            agent_results=[
                SDKAgentResult(agent_id="a1", role="Agent 1", score=90.0),
            ],
            quality_gate_results={"gate1": True},
            total_cost=0.05,
            execution_time_ms=1500.0,
        )
        data = result.to_dict()

        assert data["team_name"] == "Test Team"
        assert data["success"] is True
        assert len(data["agent_results"]) == 1
        assert data["agent_results"][0]["agent_id"] == "a1"
        assert data["quality_gate_results"]["gate1"] is True
        assert data["total_cost"] == 0.05
