"""Tests for DynamicTeam executor.

Tests all execution strategies (parallel, sequential, two_phase, delegation),
quality gate evaluation, and result aggregation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from attune.orchestration.agent_models import QualityGate, SDKAgentResult
from attune.orchestration.dynamic_team import DynamicTeam, DynamicTeamResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_agent(
    agent_id: str = "agent-1",
    role: str = "Tester",
    score: float = 90.0,
    success: bool = True,
    cost: float = 0.01,
    findings: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock SDKAgent whose process() returns a fixed result."""
    agent = MagicMock()
    agent.agent_id = agent_id
    result = SDKAgentResult(
        agent_id=agent_id,
        role=role,
        success=success,
        score=score,
        cost=cost,
        findings=findings or {"score": score},
    )
    agent.process.return_value = result
    return agent


# ---------------------------------------------------------------------------
# DynamicTeamResult
# ---------------------------------------------------------------------------


class TestDynamicTeamResult:
    """Tests for DynamicTeamResult serialization."""

    def test_to_dict(self) -> None:
        """Test that to_dict produces JSON-safe output."""
        result = DynamicTeamResult(
            team_name="test-team",
            strategy="parallel",
            success=True,
            total_cost=0.05,
            execution_time_ms=123.4,
        )
        d = result.to_dict()
        assert d["team_name"] == "test-team"
        assert d["strategy"] == "parallel"
        assert d["success"] is True
        assert d["total_cost"] == 0.05

    def test_defaults(self) -> None:
        """Test default values."""
        result = DynamicTeamResult(team_name="t", strategy="sequential")
        assert result.success is True
        assert result.agent_results == []
        assert result.quality_gate_results == {}
        assert result.phase_results == []


# ---------------------------------------------------------------------------
# Parallel strategy
# ---------------------------------------------------------------------------


class TestDynamicTeamParallel:
    """Tests for parallel execution strategy."""

    async def test_parallel_runs_all_agents(self) -> None:
        """Test that parallel executes every agent."""
        agents = [_make_mock_agent(f"a{i}", f"Role{i}") for i in range(3)]
        team = DynamicTeam(
            team_name="parallel-team",
            agents=agents,
            strategy="parallel",
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 3
        for agent in agents:
            agent.process.assert_called_once_with({"data": "test"})

    async def test_parallel_aggregates_cost(self) -> None:
        """Test that total_cost sums individual agent costs."""
        agents = [
            _make_mock_agent("a1", cost=0.01),
            _make_mock_agent("a2", cost=0.02),
        ]
        team = DynamicTeam(
            team_name="cost-team",
            agents=agents,
            strategy="parallel",
        )

        result = await team.execute({"data": "test"})

        assert abs(result.total_cost - 0.03) < 1e-9

    async def test_parallel_records_execution_time(self) -> None:
        """Test that execution_time_ms is populated."""
        team = DynamicTeam(
            team_name="time-team",
            agents=[_make_mock_agent()],
            strategy="parallel",
        )

        result = await team.execute({"data": "test"})

        assert result.execution_time_ms >= 0  # Can be 0.0 on Windows CI


# ---------------------------------------------------------------------------
# Sequential strategy
# ---------------------------------------------------------------------------


class TestDynamicTeamSequential:
    """Tests for sequential execution strategy."""

    async def test_sequential_runs_all_agents(self) -> None:
        """Test that sequential executes every agent in order."""
        agents = [_make_mock_agent(f"s{i}", f"Role{i}") for i in range(3)]
        team = DynamicTeam(
            team_name="seq-team",
            agents=agents,
            strategy="sequential",
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 3
        for agent in agents:
            agent.process.assert_called_once()

    async def test_sequential_preserves_order(self) -> None:
        """Test that results are in agent order."""
        agents = [_make_mock_agent(f"agent-{i}", f"Role-{i}") for i in range(3)]
        team = DynamicTeam(
            team_name="order-team",
            agents=agents,
            strategy="sequential",
        )

        result = await team.execute({"data": "test"})

        roles = [r.role for r in result.agent_results]
        assert roles == ["Role-0", "Role-1", "Role-2"]


# ---------------------------------------------------------------------------
# Two-phase strategy
# ---------------------------------------------------------------------------


class TestDynamicTeamTwoPhase:
    """Tests for two_phase execution strategy."""

    async def test_two_phase_with_explicit_phases(self) -> None:
        """Test two-phase with explicit phase definitions."""
        agents = [
            _make_mock_agent("gather-1", "Gatherer-1"),
            _make_mock_agent("gather-2", "Gatherer-2"),
            _make_mock_agent("reason-1", "Reasoner"),
        ]
        phases = [
            {"agent_indices": [0, 1]},
            {"agent_indices": [2]},
        ]
        team = DynamicTeam(
            team_name="two-phase-team",
            agents=agents,
            strategy="two_phase",
            phases=phases,
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 3
        assert len(result.phase_results) == 2
        assert result.phase_results[0]["phase"] == 1
        assert result.phase_results[0]["agent_count"] == 2
        assert result.phase_results[1]["phase"] == 2
        assert result.phase_results[1]["agent_count"] == 1

    async def test_two_phase_default_split(self) -> None:
        """Test two-phase with default split (first half / second half)."""
        agents = [_make_mock_agent(f"a{i}", f"R{i}") for i in range(4)]
        team = DynamicTeam(
            team_name="split-team",
            agents=agents,
            strategy="two_phase",
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 4
        # Default split: first 2 agents in phase 1, last 2 in phase 2
        assert result.phase_results[0]["agent_count"] == 2
        assert result.phase_results[1]["agent_count"] == 2

    async def test_two_phase_enriches_input_for_phase2(self) -> None:
        """Test that phase 2 agents receive phase 1 findings."""
        phase1_agent = _make_mock_agent("gather", "Gatherer", findings={"issues": ["bug-1"]})
        phase2_agent = _make_mock_agent("reason", "Reasoner")
        phases = [
            {"agent_indices": [0]},
            {"agent_indices": [1]},
        ]
        team = DynamicTeam(
            team_name="enrich-team",
            agents=[phase1_agent, phase2_agent],
            strategy="two_phase",
            phases=phases,
        )

        await team.execute({"data": "test"})

        # Phase 2 agent should receive enriched input with phase1_findings
        call_args = phase2_agent.process.call_args[0][0]
        assert "phase1_findings" in call_args


# ---------------------------------------------------------------------------
# Delegation strategy
# ---------------------------------------------------------------------------


class TestDynamicTeamDelegation:
    """Tests for delegation execution strategy."""

    async def test_delegation_coordinator_runs_first(self) -> None:
        """Test that first agent runs before delegates."""
        coordinator = _make_mock_agent("coord", "Coordinator", findings={"plan": "do X"})
        delegate = _make_mock_agent("del-1", "Delegate-1")
        team = DynamicTeam(
            team_name="delegation-team",
            agents=[coordinator, delegate],
            strategy="delegation",
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 2
        coordinator.process.assert_called_once()
        delegate.process.assert_called_once()

    async def test_delegation_passes_coordinator_findings(self) -> None:
        """Test that delegates receive coordinator findings."""
        coordinator = _make_mock_agent("coord", "Coordinator", findings={"plan": "review code"})
        delegate = _make_mock_agent("del", "Delegate")
        team = DynamicTeam(
            team_name="delegate-team",
            agents=[coordinator, delegate],
            strategy="delegation",
        )

        await team.execute({"data": "test"})

        call_args = delegate.process.call_args[0][0]
        assert "coordinator_findings" in call_args
        assert call_args["coordinator_findings"]["plan"] == "review code"

    async def test_delegation_empty_agents(self) -> None:
        """Test delegation with no agents returns empty results."""
        team = DynamicTeam(
            team_name="empty-team",
            agents=[],
            strategy="delegation",
        )

        result = await team.execute({"data": "test"})

        assert result.agent_results == []


# ---------------------------------------------------------------------------
# Unknown strategy falls back to parallel
# ---------------------------------------------------------------------------


class TestDynamicTeamFallback:
    """Tests for unknown strategy fallback."""

    async def test_unknown_strategy_falls_back_to_parallel(self) -> None:
        """Test that unrecognized strategy defaults to parallel."""
        agents = [_make_mock_agent("a1", "Role1")]
        team = DynamicTeam(
            team_name="fallback-team",
            agents=agents,
            strategy="unknown_strategy",
        )

        result = await team.execute({"data": "test"})

        assert len(result.agent_results) == 1
        agents[0].process.assert_called_once()


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------


class TestDynamicTeamQualityGates:
    """Tests for quality gate evaluation."""

    async def test_passing_gate(self) -> None:
        """Test that a satisfied gate produces success=True."""
        agent = _make_mock_agent("a1", "Auditor", score=90.0, findings={"score": 90.0})
        gate = QualityGate(
            name="min_score",
            agent_role="Auditor",
            metric="score",
            threshold=80.0,
            required=True,
        )
        team = DynamicTeam(
            team_name="gate-pass",
            agents=[agent],
            strategy="sequential",
            quality_gates=[gate],
        )

        result = await team.execute({"data": "test"})

        assert result.success is True
        assert result.quality_gate_results["min_score"] is True

    async def test_failing_required_gate(self) -> None:
        """Test that a failed required gate makes success=False."""
        agent = _make_mock_agent("a1", "Auditor", score=50.0, findings={"score": 50.0})
        gate = QualityGate(
            name="min_score",
            agent_role="Auditor",
            metric="score",
            threshold=80.0,
            required=True,
        )
        team = DynamicTeam(
            team_name="gate-fail",
            agents=[agent],
            strategy="sequential",
            quality_gates=[gate],
        )

        result = await team.execute({"data": "test"})

        assert result.success is False
        assert result.quality_gate_results["min_score"] is False

    async def test_failing_optional_gate_still_succeeds(self) -> None:
        """Test that a failed optional gate does not fail the team."""
        agent = _make_mock_agent("a1", "Auditor", score=50.0, findings={"score": 50.0})
        gate = QualityGate(
            name="nice_to_have",
            agent_role="Auditor",
            metric="score",
            threshold=80.0,
            required=False,
        )
        team = DynamicTeam(
            team_name="optional-gate",
            agents=[agent],
            strategy="sequential",
            quality_gates=[gate],
        )

        result = await team.execute({"data": "test"})

        assert result.success is True
        assert result.quality_gate_results["nice_to_have"] is False

    async def test_gate_missing_agent_role(self) -> None:
        """Test that gate referencing unknown role fails."""
        agent = _make_mock_agent("a1", "Auditor", score=90.0)
        gate = QualityGate(
            name="ghost_gate",
            agent_role="NonexistentRole",
            metric="score",
            threshold=50.0,
            required=True,
        )
        team = DynamicTeam(
            team_name="missing-role",
            agents=[agent],
            strategy="sequential",
            quality_gates=[gate],
        )

        result = await team.execute({"data": "test"})

        assert result.quality_gate_results["ghost_gate"] is False
        assert result.success is False

    async def test_no_gates_always_succeeds(self) -> None:
        """Test that no gates means success=True."""
        agent = _make_mock_agent("a1", "Role", score=10.0)
        team = DynamicTeam(
            team_name="no-gates",
            agents=[agent],
            strategy="sequential",
        )

        result = await team.execute({"data": "test"})

        assert result.success is True

    async def test_gate_with_empty_agent_role_checks_all(self) -> None:
        """Test that a gate with empty agent_role checks all agents."""
        agents = [
            _make_mock_agent("a1", "Role1", score=90.0, findings={"score": 90.0}),
            _make_mock_agent("a2", "Role2", score=85.0, findings={"score": 85.0}),
        ]
        gate = QualityGate(
            name="all_min_score",
            agent_role="",
            metric="score",
            threshold=80.0,
            required=True,
        )
        team = DynamicTeam(
            team_name="all-check",
            agents=agents,
            strategy="sequential",
            quality_gates=[gate],
        )

        result = await team.execute({"data": "test"})

        assert result.quality_gate_results["all_min_score"] is True
        assert result.success is True
