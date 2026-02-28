"""Tests for DynamicTeamBuilder.

Tests build_from_spec, build_from_plan, build_from_config, and
agent instantiation with template resolution.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from attune.agents.sdk.sdk_agent import SDKAgent
from attune.agents.sdk.sdk_models import SDKExecutionMode
from attune.orchestration.config_store import AgentConfiguration
from attune.orchestration.dynamic_team import DynamicTeam
from attune.orchestration.team_builder import DynamicTeamBuilder
from attune.orchestration.team_store import TeamSpecification

# ---------------------------------------------------------------------------
# build_from_spec
# ---------------------------------------------------------------------------


class TestBuildFromSpec:
    """Tests for DynamicTeamBuilder.build_from_spec."""

    def test_builds_team_from_spec(self) -> None:
        """Test that build_from_spec produces a DynamicTeam."""
        spec = TeamSpecification(
            name="test-team",
            agents=[{"role": "Auditor"}, {"role": "Reviewer"}],
            strategy="parallel",
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert isinstance(team, DynamicTeam)
        assert team.team_name == "test-team"
        assert team.strategy == "parallel"
        assert len(team.agents) == 2

    def test_agents_are_sdk_agents(self) -> None:
        """Test that instantiated agents are SDKAgent instances."""
        spec = TeamSpecification(
            name="sdk-team",
            agents=[{"role": "Agent-A"}],
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert len(team.agents) == 1
        assert isinstance(team.agents[0], SDKAgent)
        assert team.agents[0].role == "Agent-A"

    def test_spec_with_quality_gates(self) -> None:
        """Test that quality gates from spec are passed to the team."""
        spec = TeamSpecification(
            name="gated-team",
            agents=[{"role": "Auditor"}],
            quality_gates={
                "min_score": {
                    "agent_role": "Auditor",
                    "metric": "score",
                    "threshold": 80.0,
                    "required": True,
                },
            },
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert len(team.quality_gates) == 1
        assert team.quality_gates[0].name == "min_score"
        assert team.quality_gates[0].threshold == 80.0

    def test_spec_with_phases(self) -> None:
        """Test that phases from spec are forwarded to DynamicTeam."""
        spec = TeamSpecification(
            name="phased-team",
            agents=[{"role": "Gatherer"}, {"role": "Reasoner"}],
            strategy="two_phase",
            phases=[
                {"agent_indices": [0]},
                {"agent_indices": [1]},
            ],
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert team.strategy == "two_phase"
        assert len(team.phases) == 2

    def test_state_store_passed_to_agents(self, tmp_path: Path) -> None:
        """Test that state_store is forwarded to agents."""
        from attune.agents.state.store import AgentStateStore

        store = AgentStateStore(storage_dir=str(tmp_path))
        spec = TeamSpecification(
            name="stateful-team",
            agents=[{"role": "Stateful"}],
        )
        builder = DynamicTeamBuilder(state_store=store)
        team = builder.build_from_spec(spec)

        assert team.agents[0].state_store is store

    def test_redis_client_passed_to_agents(self) -> None:
        """Test that redis_client is forwarded to agents."""
        mock_redis = MagicMock()
        spec = TeamSpecification(
            name="redis-team",
            agents=[{"role": "Connected"}],
        )
        builder = DynamicTeamBuilder(redis_client=mock_redis)
        team = builder.build_from_spec(spec)

        assert team.agents[0].redis is mock_redis


# ---------------------------------------------------------------------------
# build_from_plan
# ---------------------------------------------------------------------------


class TestBuildFromPlan:
    """Tests for DynamicTeamBuilder.build_from_plan."""

    def test_builds_team_from_plan_dict(self) -> None:
        """Test building from a MetaOrchestrator-style plan dict."""
        plan = {
            "name": "plan-team",
            "strategy": "sequential",
            "agents": [
                {"role": "Analyzer"},
                {"role": "Reporter"},
            ],
            "quality_gates": {"min_score": 80.0},
            "phases": [],
        }
        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        assert isinstance(team, DynamicTeam)
        assert team.team_name == "plan-team"
        assert team.strategy == "sequential"
        assert len(team.agents) == 2

    def test_plan_defaults(self) -> None:
        """Test that missing plan fields get defaults."""
        plan: dict[str, Any] = {"agents": [{"role": "Solo"}]}
        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        assert team.team_name == "dynamic-team"
        assert team.strategy == "parallel"
        assert team.phases == []

    def test_plan_with_template_id(self) -> None:
        """Test that template_id is resolved to template defaults."""
        plan = {
            "agents": [
                {"template_id": "security_auditor"},
            ],
        }
        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        # security_auditor template has role "Security Auditor"
        assert team.agents[0].role == "Security Auditor"

    def test_plan_role_overrides_template(self) -> None:
        """Test that explicit role overrides template role."""
        plan = {
            "agents": [
                {"template_id": "security_auditor", "role": "Custom Role"},
            ],
        }
        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        assert team.agents[0].role == "Custom Role"

    def test_plan_quality_gates_shorthand(self) -> None:
        """Test simple threshold shorthand in quality gates."""
        plan = {
            "agents": [{"role": "Agent"}],
            "quality_gates": {"min_score": 75.0},
        }
        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        assert len(team.quality_gates) == 1
        gate = team.quality_gates[0]
        assert gate.name == "min_score"
        assert gate.threshold == 75.0
        assert gate.agent_role == ""
        assert gate.required is True


# ---------------------------------------------------------------------------
# build_from_config
# ---------------------------------------------------------------------------


class TestBuildFromConfig:
    """Tests for DynamicTeamBuilder.build_from_config."""

    def test_builds_team_from_config(self) -> None:
        """Test building from a saved AgentConfiguration."""
        config = AgentConfiguration(
            id="config-team",
            task_pattern="testing",
            agents=[{"role": "Tester"}],
            strategy="parallel",
            quality_gates={"min_coverage": 80.0},
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_config(config)

        assert isinstance(team, DynamicTeam)
        assert team.team_name == "config-team"
        assert team.strategy == "parallel"
        assert len(team.agents) == 1

    def test_config_quality_gates_converted(self) -> None:
        """Test that config quality gates are converted to QualityGate objects."""
        config = AgentConfiguration(
            id="gated-config",
            task_pattern="security",
            agents=[{"role": "Auditor"}],
            strategy="sequential",
            quality_gates={
                "security_check": {
                    "agent_role": "Auditor",
                    "metric": "vuln_score",
                    "threshold": 90.0,
                    "required": True,
                },
            },
        )
        builder = DynamicTeamBuilder()
        team = builder.build_from_config(config)

        assert len(team.quality_gates) == 1
        assert team.quality_gates[0].name == "security_check"
        assert team.quality_gates[0].metric == "vuln_score"


# ---------------------------------------------------------------------------
# Agent instantiation
# ---------------------------------------------------------------------------


class TestInstantiateAgent:
    """Tests for agent instantiation and template resolution."""

    def test_agent_with_no_template(self) -> None:
        """Test agent creation without a template."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent({"role": "Custom Agent"})

        assert isinstance(agent, SDKAgent)
        assert agent.role == "Custom Agent"

    def test_agent_with_unknown_template(self) -> None:
        """Test that unknown template_id falls back gracefully."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent(
            {
                "template_id": "nonexistent_template",
                "role": "Fallback",
            },
        )

        # Should still create agent with the provided role
        assert agent.role == "Fallback"

    def test_agent_with_valid_template(self) -> None:
        """Test agent picks up template defaults."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent(
            {
                "template_id": "code_reviewer",
            },
        )

        assert agent.role == "Code Quality Reviewer"

    def test_agent_mode_parsing(self) -> None:
        """Test that mode string is parsed to SDKExecutionMode."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent(
            {
                "role": "SDK Agent",
                "mode": "full_sdk",
            },
        )

        assert agent.mode == SDKExecutionMode.FULL_SDK

    def test_agent_invalid_mode_defaults(self) -> None:
        """Test that invalid mode defaults to TOOLS_ONLY."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent(
            {
                "role": "Agent",
                "mode": "invalid_mode",
            },
        )

        assert agent.mode == SDKExecutionMode.TOOLS_ONLY

    def test_agent_id_from_spec(self) -> None:
        """Test that explicit agent_id is preserved."""
        builder = DynamicTeamBuilder()
        agent = builder._instantiate_agent(
            {
                "agent_id": "my-custom-id",
                "role": "Agent",
            },
        )

        assert agent.agent_id == "my-custom-id"


# ---------------------------------------------------------------------------
# Quality gate building
# ---------------------------------------------------------------------------


class TestBuildQualityGates:
    """Tests for _build_quality_gates."""

    def test_empty_spec(self) -> None:
        """Test empty gate spec returns empty list."""
        builder = DynamicTeamBuilder()
        gates = builder._build_quality_gates({})
        assert gates == []

    def test_shorthand_spec(self) -> None:
        """Test simple threshold shorthand."""
        builder = DynamicTeamBuilder()
        gates = builder._build_quality_gates({"min_score": 80.0})

        assert len(gates) == 1
        assert gates[0].name == "min_score"
        assert gates[0].threshold == 80.0
        assert gates[0].agent_role == ""
        assert gates[0].metric == "score"
        assert gates[0].required is True

    def test_detailed_spec(self) -> None:
        """Test detailed gate specification."""
        builder = DynamicTeamBuilder()
        gates = builder._build_quality_gates(
            {
                "security_gate": {
                    "agent_role": "Security Auditor",
                    "metric": "vulnerability_score",
                    "threshold": 95.0,
                    "required": False,
                },
            },
        )

        assert len(gates) == 1
        gate = gates[0]
        assert gate.name == "security_gate"
        assert gate.agent_role == "Security Auditor"
        assert gate.metric == "vulnerability_score"
        assert gate.threshold == 95.0
        assert gate.required is False

    def test_mixed_specs(self) -> None:
        """Test mix of shorthand and detailed specs."""
        builder = DynamicTeamBuilder()
        gates = builder._build_quality_gates(
            {
                "simple_gate": 70.0,
                "detailed_gate": {
                    "agent_role": "Reviewer",
                    "metric": "quality",
                    "threshold": 85.0,
                },
            },
        )

        assert len(gates) == 2
        names = {g.name for g in gates}
        assert names == {"simple_gate", "detailed_gate"}
