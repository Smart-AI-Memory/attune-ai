"""Smoke tests for all workflows, agents, teams, and orchestration.

Verifies that every registered workflow can be instantiated, every agent
class can be created, every team builder works, and the full Phase 1-4
agent orchestration pipeline functions end-to-end.

No API key required — agents use rule-based fallback when no LLM is available.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Any

import pytest
from dotenv import load_dotenv

# Load API key from .env for tests that require it
load_dotenv()

from attune.workflows import get_workflow, list_workflows  # noqa: E402

# ---------------------------------------------------------------------------
# Workflow classification constants
# ---------------------------------------------------------------------------

# BaseWorkflow subclasses that accept provider= and state_store= kwargs
BASEWORKFLOW_NAMES = [
    "code-review",
    "doc-gen",
    "bug-predict",
    "security-audit",
    "perf-audit",
    "test-gen",
    "refactor-plan",
    "dependency-check",
    "keyboard-shortcuts",
    "research-synthesis",
]

# Workflows that need special constructor arguments
SPECIAL_CONSTRUCTOR_ARGS: dict[str, dict[str, Any]] = {
    "test-maintenance": {"project_root": "."},
    "batch-processing": {
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    },
}

# Workflows that cannot be instantiated in tests
SKIP_INSTANTIATION = {
    "test-gen-parallel",  # Abstract class with abstract run_stage
}

# Workflows that require an API key (skip only if key unavailable)
API_KEY_REQUIRED = {
    "batch-processing",  # Requires ANTHROPIC_API_KEY env var
}

# Workflows whose instances lack a `name` attribute
NO_NAME_ATTRIBUTE = {
    "orchestrated-health-check",
    "batch-processing",
}


# ===========================================================================
# Section 1: Workflow Registry
# ===========================================================================


class TestWorkflowRegistry:
    """Test that workflow registry works correctly."""

    def test_list_workflows_returns_workflows(self):
        """Test that listing workflows returns a non-empty list."""
        workflows = list_workflows()

        assert isinstance(workflows, list)
        assert len(workflows) > 0
        assert all(isinstance(w, dict) for w in workflows)
        assert all("name" in w for w in workflows)

    def test_get_workflow_by_name_works(self):
        """Test that getting a workflow by name doesn't crash."""
        workflows = list_workflows()

        if workflows:
            # Pick a known BaseWorkflow subclass
            workflow_class = get_workflow("code-review")

            assert workflow_class is not None
            assert hasattr(workflow_class, "name")
            assert hasattr(workflow_class, "description")

    def test_all_workflows_resolvable(self):
        """Test that all registered workflows can be resolved by get_workflow."""
        workflows = list_workflows()

        for workflow_info in workflows:
            workflow_class = get_workflow(workflow_info["name"])
            assert workflow_class is not None, f"{workflow_info['name']} resolved to None"

    def test_minimum_workflow_count(self):
        """Test that at least 15 workflows are registered."""
        workflows = list_workflows()
        assert len(workflows) >= 15, f"Expected >= 15 workflows, got {len(workflows)}"


# ===========================================================================
# Section 2: All Workflows Can Instantiate
# ===========================================================================


# Expected registered workflow names (from _DEFAULT_WORKFLOW_NAMES)
# Note: Consolidated slugs (pro-review, pr-review, document-manager,
# orchestrated-release-prep, autonomous-test-gen, progressive-test-gen,
# test-coverage-boost) are handled by the migration system and no longer
# appear in the active registry.
EXPECTED_WORKFLOWS = [
    "code-review",
    "doc-gen",
    "doc-orchestrator",
    "seo-optimization",
    "bug-predict",
    "security-audit",
    "perf-audit",
    "test-gen",
    "test-gen-parallel",
    "refactor-plan",
    "dependency-check",
    "secure-release",
    "keyboard-shortcuts",
    "orchestrated-health-check",
    "release-prep",
    "research-synthesis",
    "test-maintenance",
    "batch-processing",
]


class TestAllWorkflowsCanInstantiate:
    """Test that every registered workflow can be instantiated."""

    @pytest.mark.parametrize("workflow_name", EXPECTED_WORKFLOWS)
    def test_workflow_can_instantiate(self, workflow_name: str):
        """Test that workflow can be instantiated without crashing."""
        if workflow_name in SKIP_INSTANTIATION:
            pytest.skip(f"'{workflow_name}' cannot be instantiated in tests")
        if workflow_name in API_KEY_REQUIRED and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip(f"'{workflow_name}' requires ANTHROPIC_API_KEY")

        try:
            workflow_class = get_workflow(workflow_name)
        except KeyError:
            pytest.skip(f"Workflow '{workflow_name}' not in registry")

        kwargs = SPECIAL_CONSTRUCTOR_ARGS.get(workflow_name, {})
        workflow = workflow_class(**kwargs)

        # Not all workflows have name/description (non-BaseWorkflow classes)
        if workflow_name not in NO_NAME_ATTRIBUTE:
            assert hasattr(workflow, "name"), f"{workflow_name} missing 'name'"

    @pytest.mark.parametrize("workflow_name", BASEWORKFLOW_NAMES)
    def test_baseworkflow_accepts_provider_parameter(self, workflow_name: str):
        """Test that BaseWorkflow subclasses accept provider='anthropic'."""
        try:
            workflow_class = get_workflow(workflow_name)
        except KeyError:
            pytest.skip(f"Workflow '{workflow_name}' not in registry")

        workflow = workflow_class(provider="anthropic")
        assert hasattr(workflow, "_provider_str") or hasattr(workflow, "provider")

    @pytest.mark.parametrize("workflow_name", BASEWORKFLOW_NAMES)
    def test_baseworkflow_accepts_state_store_parameter(self, workflow_name: str):
        """Test that BaseWorkflow subclasses accept state_store=None (Phase 4a)."""
        try:
            workflow_class = get_workflow(workflow_name)
        except KeyError:
            pytest.skip(f"Workflow '{workflow_name}' not in registry")

        workflow = workflow_class(state_store=None)
        assert workflow._state_store is None


class TestWorkflowDescribeMethod:
    """Test workflow describe() method on BaseWorkflow subclasses."""

    @pytest.mark.parametrize("workflow_name", BASEWORKFLOW_NAMES)
    def test_baseworkflow_can_describe(self, workflow_name: str):
        """Test that BaseWorkflow subclasses with describe() produce output."""
        try:
            workflow_class = get_workflow(workflow_name)
        except KeyError:
            pytest.skip(f"Workflow '{workflow_name}' not in registry")

        workflow = workflow_class()
        if hasattr(workflow, "describe"):
            description = workflow.describe()
            assert isinstance(description, str)
            assert len(description) > 0, f"{workflow_name}.describe() returned empty string"


# ===========================================================================
# Section 3: Agent Classes
# ===========================================================================


class TestReleaseAgents:
    """Test release agent classes can be instantiated."""

    def test_release_agent_instantiate(self):
        """Test ReleaseAgent base class."""
        from attune.agents.release.release_agents import ReleaseAgent

        agent = ReleaseAgent(agent_id="test-01", role="test-agent")
        assert agent.role == "test-agent"
        assert agent.current_tier is not None

    def test_security_auditor_agent(self):
        """Test SecurityAuditorAgent specialization."""
        from attune.agents.release.release_agents import SecurityAuditorAgent

        agent = SecurityAuditorAgent()
        assert agent.role == "Security Auditor"

    def test_test_coverage_agent(self):
        """Test TestCoverageAgent specialization."""
        from attune.agents.release.release_agents import TestCoverageAgent

        agent = TestCoverageAgent()
        assert agent.role == "Test Coverage"

    def test_code_quality_agent(self):
        """Test CodeQualityAgent specialization."""
        from attune.agents.release.release_agents import CodeQualityAgent

        agent = CodeQualityAgent()
        assert agent.role == "Code Quality"

    def test_documentation_agent(self):
        """Test DocumentationAgent specialization."""
        from attune.agents.release.release_agents import DocumentationAgent

        agent = DocumentationAgent()
        assert agent.role == "Documentation"

    def test_release_agent_accepts_state_store(self):
        """Test ReleaseAgent accepts state_store parameter."""
        from attune.agents.release.release_agents import ReleaseAgent

        agent = ReleaseAgent(agent_id="test-02", role="test", state_store=None)
        assert agent.state_store is None


class TestSDKAgent:
    """Test SDK agent classes (Phase 2)."""

    def test_sdk_agent_instantiate(self):
        """Test SDKAgent can be created with defaults."""
        from attune.agents.sdk.sdk_agent import SDKAgent

        agent = SDKAgent()
        assert agent.agent_id.startswith("sdk-agent-")
        assert agent.role == "SDK Agent"

    def test_sdk_agent_custom_params(self):
        """Test SDKAgent with custom parameters."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_models import SDKExecutionMode

        agent = SDKAgent(
            agent_id="custom-agent",
            role="Custom Role",
            system_prompt="You are a test agent.",
            mode=SDKExecutionMode.TOOLS_ONLY,
        )
        assert agent.agent_id == "custom-agent"
        assert agent.role == "Custom Role"
        assert agent.mode == SDKExecutionMode.TOOLS_ONLY

    def test_sdk_agent_process_returns_result(self):
        """Test SDKAgent.process() returns SDKAgentResult."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_models import SDKAgentResult

        agent = SDKAgent(agent_id="test-process")
        result = agent.process({"task": "test"})

        assert isinstance(result, SDKAgentResult)
        assert result.agent_id == "test-process"
        assert result.tier_used in ("cheap", "capable", "premium")

    def test_sdk_agent_tier_execution(self):
        """Test SDKAgent processes input and returns valid tier info."""
        from attune.agents.sdk.sdk_agent import SDKAgent

        agent = SDKAgent(agent_id="test-tier")
        result = agent.process({"task": "tier-test"})

        # Tier should be one of the valid values regardless of escalation
        assert result.tier_used in ("cheap", "capable", "premium")
        assert result.execution_time_ms > 0

    def test_sdk_available_flag(self):
        """Test SDK_AVAILABLE flag is a boolean."""
        from attune.agents.sdk.sdk_models import SDK_AVAILABLE

        assert isinstance(SDK_AVAILABLE, bool)

    def test_sdk_execution_modes(self):
        """Test SDKExecutionMode enum values."""
        from attune.agents.sdk.sdk_models import SDKExecutionMode

        assert SDKExecutionMode.TOOLS_ONLY.value == "tools_only"
        assert SDKExecutionMode.FULL_SDK.value == "full_sdk"


class TestSDKAgentResult:
    """Test SDKAgentResult serialization."""

    def test_to_dict_roundtrip(self):
        """Test SDKAgentResult serialization/deserialization."""
        from attune.agents.sdk.sdk_models import SDKAgentResult, SDKExecutionMode

        original = SDKAgentResult(
            agent_id="test-rt",
            role="Test Agent",
            success=True,
            tier_used="capable",
            mode=SDKExecutionMode.TOOLS_ONLY,
            findings={"issues": 3},
            score=85.0,
            confidence=0.9,
            cost=0.05,
            execution_time_ms=1200.0,
            escalated=False,
            sdk_used=False,
        )

        data = original.to_dict()
        restored = SDKAgentResult.from_dict(data)

        assert restored.agent_id == original.agent_id
        assert restored.role == original.role
        assert restored.success == original.success
        assert restored.tier_used == original.tier_used
        assert restored.score == original.score
        assert restored.cost == original.cost


# ===========================================================================
# Section 4: Agent State Persistence (Phase 1)
# ===========================================================================


class TestAgentStatePersistence:
    """Test AgentStateStore CRUD and recovery."""

    def test_state_store_record_lifecycle(self):
        """Test full agent lifecycle: start -> checkpoint -> complete."""
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)

            exec_id = store.record_start("agent-01", "Security Auditor")
            assert isinstance(exec_id, str)
            assert len(exec_id) > 0

            store.save_checkpoint("agent-01", {"stage": "triage", "progress": 50})

            store.record_completion(
                "agent-01",
                exec_id,
                success=True,
                findings={"critical": 0},
                score=90.0,
                cost=0.02,
                execution_time_ms=1000.0,
                tier_used="capable",
            )

            state = store.get_agent_state("agent-01")
            assert state is not None
            assert state.total_executions == 1
            assert state.successful_executions == 1
            assert state.success_rate == 1.0

    def test_state_store_checkpoint_recovery(self):
        """Test checkpoint save and retrieval."""
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            store.record_start("agent-ckpt", "Tester")
            store.save_checkpoint(
                "agent-ckpt",
                {"completed": ["stage1"], "pending": ["stage2"]},
            )

            checkpoint = store.get_last_checkpoint("agent-ckpt")
            assert checkpoint is not None
            assert checkpoint["completed"] == ["stage1"]

    def test_state_store_search_history(self):
        """Test searching agent history by role."""
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)

            exec1 = store.record_start("sec-01", "Security Auditor")
            store.record_completion(
                "sec-01",
                exec1,
                success=True,
                findings={},
                score=90.0,
                cost=0.01,
                execution_time_ms=500.0,
            )

            exec2 = store.record_start("rev-01", "Code Reviewer")
            store.record_completion(
                "rev-01",
                exec2,
                success=True,
                findings={},
                score=85.0,
                cost=0.02,
                execution_time_ms=700.0,
            )

            sec_results = store.search_history(role="Security")
            assert len(sec_results) == 1
            assert sec_results[0].role == "Security Auditor"

    def test_state_store_get_all_agents(self):
        """Test listing all known agents."""
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            store.record_start("a1", "Role A")
            store.record_start("a2", "Role B")

            all_agents = store.get_all_agents()
            assert len(all_agents) == 2

    def test_state_store_history_trimming(self):
        """Test that history trims to MAX_HISTORY_PER_AGENT."""
        from attune.agents.state.store import MAX_HISTORY_PER_AGENT, AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)

            for _i in range(MAX_HISTORY_PER_AGENT + 20):
                store.record_start("trim-test", "Trimmer")

            state = store.get_agent_state("trim-test")
            assert state is not None
            assert len(state.execution_history) <= MAX_HISTORY_PER_AGENT


class TestAgentRecovery:
    """Test AgentRecoveryManager."""

    def test_find_interrupted_agents(self):
        """Test finding agents with incomplete executions."""
        from attune.agents.state.recovery import AgentRecoveryManager
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            store.record_start("interrupted-01", "Profiler")
            # No record_completion -> simulates crash

            recovery = AgentRecoveryManager(state_store=store)
            interrupted = recovery.find_interrupted_agents()

            assert len(interrupted) >= 1
            assert any(r.agent_id == "interrupted-01" for r in interrupted)

    def test_recover_agent_returns_checkpoint(self):
        """Test recovering an interrupted agent's checkpoint."""
        from attune.agents.state.recovery import AgentRecoveryManager
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            store.record_start("recover-01", "Analyst")
            store.save_checkpoint("recover-01", {"partial": True})

            recovery = AgentRecoveryManager(state_store=store)
            checkpoint = recovery.recover_agent("recover-01")

            assert checkpoint is not None
            assert checkpoint["partial"] is True

    def test_mark_abandoned(self):
        """Test marking interrupted agents as abandoned."""
        from attune.agents.state.recovery import AgentRecoveryManager
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            store.record_start("abandon-01", "Worker")

            recovery = AgentRecoveryManager(state_store=store)
            recovery.mark_abandoned("abandon-01")

            state = store.get_agent_state("abandon-01")
            assert state is not None
            assert any(e.status == "interrupted" for e in state.execution_history)


# ===========================================================================
# Section 5: Agent Templates (Phase 3)
# ===========================================================================


class TestAgentTemplates:
    """Test agent template registry."""

    def test_thirteen_templates_registered(self):
        """Test that 13 pre-built templates are available."""
        from attune.orchestration.agent_templates import get_all_templates

        templates = get_all_templates()
        assert len(templates) == 13

    def test_get_template_by_id(self):
        """Test retrieving a template by ID."""
        from attune.orchestration.agent_templates import get_template

        template = get_template("security_auditor")
        assert template is not None
        assert template.role == "Security Auditor"
        assert template.tier_preference == "PREMIUM"

    @pytest.mark.parametrize(
        "template_id",
        [
            "test_coverage_analyzer",
            "security_auditor",
            "code_reviewer",
            "documentation_writer",
            "performance_optimizer",
            "architecture_analyst",
            "refactoring_specialist",
            "test_generator",
            "test_validator",
            "report_generator",
            "documentation_analyst",
            "synthesizer",
            "generic_agent",
        ],
    )
    def test_template_has_valid_fields(self, template_id: str):
        """Test that each template has valid required fields."""
        from attune.orchestration.agent_templates import get_template

        template = get_template(template_id)
        assert template is not None
        assert template.id == template_id
        assert len(template.role) > 0
        assert len(template.capabilities) > 0
        assert template.tier_preference in {"CHEAP", "CAPABLE", "PREMIUM"}
        assert isinstance(template.tools, list)
        assert len(template.default_instructions) > 0
        assert isinstance(template.quality_gates, dict)

    def test_get_templates_by_tier(self):
        """Test filtering templates by tier preference."""
        from attune.orchestration.agent_templates import get_templates_by_tier

        cheap = get_templates_by_tier("CHEAP")
        capable = get_templates_by_tier("CAPABLE")
        premium = get_templates_by_tier("PREMIUM")

        assert len(cheap) > 0
        assert len(capable) > 0
        assert len(premium) > 0
        assert len(cheap) + len(capable) + len(premium) == 13

    def test_get_templates_by_capability(self):
        """Test filtering templates by capability."""
        from attune.orchestration.agent_templates import get_templates_by_capability

        vuln_templates = get_templates_by_capability("vulnerability_scan")
        assert len(vuln_templates) >= 1
        assert any(t.id == "security_auditor" for t in vuln_templates)

    def test_custom_template_registration(self):
        """Test registering and unregistering a custom template."""
        from attune.orchestration.agent_templates import (
            AgentTemplate,
            get_template,
            register_custom_template,
            unregister_template,
        )

        custom = AgentTemplate(
            id="test_custom_template",
            role="Custom Test Agent",
            capabilities=["test_capability"],
            tier_preference="CHEAP",
            tools=["test_tool"],
            default_instructions="Test instructions",
            quality_gates={"min_score": 50},
        )
        register_custom_template(custom)

        assert get_template("test_custom_template") is not None
        assert get_template("test_custom_template").role == "Custom Test Agent"

        # Cleanup
        unregister_template("test_custom_template")
        assert get_template("test_custom_template") is None

    def test_get_registry_returns_snapshot(self):
        """Test get_registry returns independent dict snapshot."""
        from attune.orchestration.agent_templates import get_registry

        registry = get_registry()
        assert isinstance(registry, dict)
        assert len(registry) == 13


# ===========================================================================
# Section 6: Agent Teams (Phase 2 + 3)
# ===========================================================================


class TestReleasePrepTeam:
    """Test ReleasePrepTeam (production agent team)."""

    def test_release_prep_team_instantiate(self):
        """Test ReleasePrepTeam can be created."""
        from attune.agents.release.release_prep_team import ReleasePrepTeam

        team = ReleasePrepTeam()
        assert len(team.agents) > 0

    def test_release_prep_team_agents_have_roles(self):
        """Test that team agents have distinct roles."""
        from attune.agents.release.release_prep_team import ReleasePrepTeam

        team = ReleasePrepTeam()
        roles = [a.role for a in team.agents]
        assert "Security Auditor" in roles
        assert "Test Coverage" in roles
        assert "Code Quality" in roles
        assert "Documentation" in roles


class TestSDKAgentTeam:
    """Test SDKAgentTeam (Phase 2)."""

    def test_sdk_team_instantiate(self):
        """Test SDKAgentTeam can be created."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_team import SDKAgentTeam

        agents = [
            SDKAgent(agent_id="a1", role="Agent 1"),
            SDKAgent(agent_id="a2", role="Agent 2"),
        ]
        team = SDKAgentTeam(
            team_name="test-team",
            agents=agents,
            parallel=True,
        )
        assert team.team_name == "test-team"
        assert len(team.agents) == 2

    def test_sdk_team_execute_parallel(self):
        """Test SDKAgentTeam parallel execution."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_team import SDKAgentTeam

        agents = [
            SDKAgent(agent_id="p1", role="Parallel 1"),
            SDKAgent(agent_id="p2", role="Parallel 2"),
        ]
        team = SDKAgentTeam(
            team_name="parallel-test",
            agents=agents,
            parallel=True,
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.team_name == "parallel-test"
        assert len(result.agent_results) == 2

    def test_sdk_team_execute_sequential(self):
        """Test SDKAgentTeam sequential execution."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_team import SDKAgentTeam

        agents = [
            SDKAgent(agent_id="s1", role="Seq 1"),
            SDKAgent(agent_id="s2", role="Seq 2"),
        ]
        team = SDKAgentTeam(
            team_name="sequential-test",
            agents=agents,
            parallel=False,
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.team_name == "sequential-test"
        assert len(result.agent_results) == 2


class TestDynamicTeam:
    """Test DynamicTeam (Phase 3)."""

    def test_dynamic_team_parallel(self):
        """Test DynamicTeam with parallel strategy."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [
            SDKAgent(agent_id="dp1", role="Agent A"),
            SDKAgent(agent_id="dp2", role="Agent B"),
        ]
        team = DynamicTeam(
            team_name="dynamic-parallel",
            agents=agents,
            strategy="parallel",
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.team_name == "dynamic-parallel"
        assert result.strategy == "parallel"
        assert len(result.agent_results) == 2
        assert result.execution_time_ms > 0

    def test_dynamic_team_sequential(self):
        """Test DynamicTeam with sequential strategy."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [
            SDKAgent(agent_id="ds1", role="Seq A"),
            SDKAgent(agent_id="ds2", role="Seq B"),
        ]
        team = DynamicTeam(
            team_name="dynamic-seq",
            agents=agents,
            strategy="sequential",
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.strategy == "sequential"
        assert len(result.agent_results) == 2

    def test_dynamic_team_two_phase(self):
        """Test DynamicTeam with two_phase strategy."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [
            SDKAgent(agent_id="g1", role="Gatherer"),
            SDKAgent(agent_id="g2", role="Gatherer 2"),
            SDKAgent(agent_id="r1", role="Reasoner"),
        ]
        team = DynamicTeam(
            team_name="two-phase-test",
            agents=agents,
            strategy="two_phase",
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.strategy == "two_phase"
        assert len(result.agent_results) == 3
        assert len(result.phase_results) == 2

    def test_dynamic_team_delegation(self):
        """Test DynamicTeam with delegation strategy."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [
            SDKAgent(agent_id="coord", role="Coordinator"),
            SDKAgent(agent_id="del1", role="Delegate 1"),
            SDKAgent(agent_id="del2", role="Delegate 2"),
        ]
        team = DynamicTeam(
            team_name="delegation-test",
            agents=agents,
            strategy="delegation",
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert result.strategy == "delegation"
        assert len(result.agent_results) == 3

    def test_dynamic_team_quality_gates(self):
        """Test DynamicTeam quality gate evaluation."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.agents.sdk.sdk_team import QualityGate
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [SDKAgent(agent_id="qg1", role="Gated Agent")]
        gates = [
            QualityGate(
                name="min_score",
                agent_role="",
                metric="score",
                threshold=50.0,
                required=True,
            )
        ]
        team = DynamicTeam(
            team_name="gated-test",
            agents=agents,
            strategy="parallel",
            quality_gates=gates,
        )
        result = asyncio.run(team.execute({"task": "test"}))

        assert "min_score" in result.quality_gate_results

    def test_dynamic_team_result_serialization(self):
        """Test DynamicTeamResult.to_dict()."""
        from attune.agents.sdk.sdk_agent import SDKAgent
        from attune.orchestration.dynamic_team import DynamicTeam

        agents = [SDKAgent(agent_id="ser1", role="Serializer")]
        team = DynamicTeam(team_name="ser-test", agents=agents)
        result = asyncio.run(team.execute({"task": "test"}))

        data = result.to_dict()
        assert isinstance(data, dict)
        assert data["team_name"] == "ser-test"
        assert isinstance(data["agent_results"], list)


# ===========================================================================
# Section 7: Dynamic Team Builder (Phase 3)
# ===========================================================================


class TestDynamicTeamBuilder:
    """Test DynamicTeamBuilder builds teams from various sources."""

    def test_build_from_spec(self):
        """Test building a team from a TeamSpecification."""
        from attune.orchestration.team_builder import DynamicTeamBuilder
        from attune.orchestration.team_store import TeamSpecification

        spec = TeamSpecification(
            name="spec-team",
            agents=[
                {"template_id": "security_auditor"},
                {"template_id": "code_reviewer"},
            ],
            strategy="parallel",
            quality_gates={"min_score": 70},
        )

        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert team.team_name == "spec-team"
        assert team.strategy == "parallel"
        assert len(team.agents) == 2

    def test_build_from_plan(self):
        """Test building a team from an execution plan dict."""
        from attune.orchestration.team_builder import DynamicTeamBuilder

        plan = {
            "name": "plan-team",
            "agents": [
                {"template_id": "test_generator"},
                {"template_id": "test_validator"},
            ],
            "strategy": "sequential",
            "quality_gates": {},
        }

        builder = DynamicTeamBuilder()
        team = builder.build_from_plan(plan)

        assert team.team_name == "plan-team"
        assert team.strategy == "sequential"
        assert len(team.agents) == 2

    def test_build_from_spec_with_state_store(self):
        """Test that builder forwards state_store to agents."""
        from attune.agents.state.store import AgentStateStore
        from attune.orchestration.team_builder import DynamicTeamBuilder
        from attune.orchestration.team_store import TeamSpecification

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            builder = DynamicTeamBuilder(state_store=store)

            spec = TeamSpecification(
                name="stateful-team",
                agents=[{"template_id": "generic_agent"}],
                strategy="parallel",
                quality_gates={},
            )
            team = builder.build_from_spec(spec)

            assert len(team.agents) == 1
            assert team.agents[0].state_store is store

    def test_build_all_template_types(self):
        """Test that all 13 templates can be instantiated as agents."""
        from attune.orchestration.agent_templates import get_all_templates
        from attune.orchestration.team_builder import DynamicTeamBuilder
        from attune.orchestration.team_store import TeamSpecification

        templates = get_all_templates()

        spec = TeamSpecification(
            name="all-templates-team",
            agents=[{"template_id": t.id} for t in templates],
            strategy="parallel",
            quality_gates={},
        )

        builder = DynamicTeamBuilder()
        team = builder.build_from_spec(spec)

        assert len(team.agents) == 13


# ===========================================================================
# Section 8: Team Store (Phase 3)
# ===========================================================================


class TestTeamStore:
    """Test TeamStore persistence."""

    def test_save_and_load_spec(self):
        """Test saving and loading a TeamSpecification."""
        from attune.orchestration.team_store import TeamSpecification, TeamStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = TeamStore(storage_dir=tmp_dir)

            spec = TeamSpecification(
                name="saved-team",
                agents=[{"template_id": "code_reviewer"}],
                strategy="parallel",
                quality_gates={"min_score": 80},
            )

            store.save(spec)
            loaded = store.load("saved-team")

            assert loaded is not None
            assert loaded.name == "saved-team"
            assert loaded.strategy == "parallel"
            assert len(loaded.agents) == 1

    def test_list_all_teams(self):
        """Test listing all saved team specs."""
        from attune.orchestration.team_store import TeamSpecification, TeamStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = TeamStore(storage_dir=tmp_dir)
            store.save(
                TeamSpecification(
                    name="team-a",
                    agents=[{"template_id": "generic_agent"}],
                    strategy="parallel",
                    quality_gates={},
                )
            )
            store.save(
                TeamSpecification(
                    name="team-b",
                    agents=[{"template_id": "code_reviewer"}],
                    strategy="sequential",
                    quality_gates={},
                )
            )

            all_teams = store.list_all()
            assert len(all_teams) == 2

    def test_delete_team(self):
        """Test deleting a saved team spec."""
        from attune.orchestration.team_store import TeamSpecification, TeamStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = TeamStore(storage_dir=tmp_dir)
            store.save(
                TeamSpecification(
                    name="to-delete",
                    agents=[{"template_id": "generic_agent"}],
                    strategy="parallel",
                    quality_gates={},
                )
            )

            assert store.delete("to-delete") is True
            assert store.load("to-delete") is None


# ===========================================================================
# Section 9: Workflow Composition (Phase 4)
# ===========================================================================


class TestWorkflowAgentAdapter:
    """Test WorkflowAgentAdapter wrapping workflows as agents."""

    def test_adapter_creation(self):
        """Test WorkflowAgentAdapter can be created."""
        from attune.orchestration.workflow_agent_adapter import WorkflowAgentAdapter

        WorkflowClass = get_workflow("code-review")
        adapter = WorkflowAgentAdapter(
            workflow_class=WorkflowClass,
            role="Code Review Agent",
        )
        assert adapter.role == "Code Review Agent"
        assert adapter.agent_id.startswith("wf-adapter-")

    def test_adapter_custom_agent_id(self):
        """Test WorkflowAgentAdapter with custom agent_id."""
        from attune.orchestration.workflow_agent_adapter import WorkflowAgentAdapter

        WorkflowClass = get_workflow("security-audit")
        adapter = WorkflowAgentAdapter(
            workflow_class=WorkflowClass,
            agent_id="sec-audit-adapter",
            role="Security Audit",
        )
        assert adapter.agent_id == "sec-audit-adapter"


class TestWorkflowComposer:
    """Test WorkflowComposer composing workflows into teams."""

    def test_composer_creation(self):
        """Test WorkflowComposer can be created."""
        from attune.orchestration.workflow_composer import WorkflowComposer

        composer = WorkflowComposer()
        assert composer.state_store is None

    def test_composer_with_state_store(self):
        """Test WorkflowComposer with state_store."""
        from attune.agents.state.store import AgentStateStore
        from attune.orchestration.workflow_composer import WorkflowComposer

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            composer = WorkflowComposer(state_store=store)
            assert composer.state_store is store

    def test_composer_compose_creates_team(self):
        """Test compose() creates a DynamicTeam from workflows."""
        from attune.orchestration.dynamic_team import DynamicTeam
        from attune.orchestration.workflow_composer import WorkflowComposer

        composer = WorkflowComposer()
        team = composer.compose(
            team_name="composed-review",
            workflows=[
                {"workflow": get_workflow("code-review"), "role": "Code Reviewer"},
                {"workflow": get_workflow("security-audit"), "role": "Security Audit"},
            ],
            strategy="parallel",
        )

        assert isinstance(team, DynamicTeam)
        assert team.team_name == "composed-review"
        assert team.strategy == "parallel"
        assert len(team.agents) == 2

    def test_composer_rejects_empty_workflows(self):
        """Test compose() raises ValueError for empty workflows."""
        from attune.orchestration.workflow_composer import WorkflowComposer

        composer = WorkflowComposer()
        with pytest.raises(ValueError, match="At least one workflow"):
            composer.compose(
                team_name="empty",
                workflows=[],
            )


# ===========================================================================
# Section 10: Execution Strategies
# ===========================================================================


class TestExecutionStrategies:
    """Test orchestration execution strategies."""

    def test_get_strategy_tool_enhanced(self):
        """Test loading tool_enhanced strategy."""
        from attune.orchestration.execution_strategies import get_strategy

        strategy = get_strategy("tool_enhanced")
        assert strategy is not None

    def test_get_strategy_prompt_cached(self):
        """Test loading prompt_cached_sequential strategy."""
        from attune.orchestration.execution_strategies import get_strategy

        strategy = get_strategy("prompt_cached_sequential")
        assert strategy is not None

    def test_get_strategy_delegation_chain(self):
        """Test loading delegation_chain strategy."""
        from attune.orchestration.execution_strategies import get_strategy

        strategy = get_strategy("delegation_chain")
        assert strategy is not None


# ===========================================================================
# Section 11: Meta-Orchestrator
# ===========================================================================


class TestMetaOrchestrator:
    """Test MetaOrchestrator task analysis."""

    def test_meta_orchestrator_instantiate(self):
        """Test MetaOrchestrator can be created."""
        from attune.orchestration.meta_orchestrator import MetaOrchestrator

        orch = MetaOrchestrator()
        assert orch is not None

    def test_task_requirements_creation(self):
        """Test TaskRequirements dataclass."""
        from attune.orchestration.meta_orchestrator import (
            TaskComplexity,
            TaskDomain,
            TaskRequirements,
        )

        reqs = TaskRequirements(
            domain=TaskDomain.SECURITY,
            complexity=TaskComplexity.MODERATE,
            capabilities_needed=["vulnerability_scan"],
        )
        assert reqs.domain == TaskDomain.SECURITY
        assert reqs.complexity == TaskComplexity.MODERATE
        assert "vulnerability_scan" in reqs.capabilities_needed


# ===========================================================================
# Section 12: State Persistence Mixin in Workflows (Phase 4a)
# ===========================================================================


class TestStatePersistenceMixin:
    """Test StatePersistenceMixin integration with BaseWorkflow."""

    def test_workflow_has_state_store_attribute(self):
        """Test that all workflows accept state_store parameter."""
        WorkflowClass = get_workflow("code-review")
        workflow = WorkflowClass(state_store=None)
        assert workflow._state_store is None

    def test_workflow_with_state_store(self):
        """Test workflow with an actual AgentStateStore."""
        from attune.agents.state.store import AgentStateStore

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = AgentStateStore(storage_dir=tmp_dir)
            WorkflowClass = get_workflow("code-review")
            workflow = WorkflowClass(state_store=store)
            assert workflow._state_store is store


class TestMultiAgentStageMixin:
    """Test MultiAgentStageMixin integration with BaseWorkflow."""

    def test_workflow_accepts_multi_agent_configs(self):
        """Test that workflow accepts multi_agent_configs parameter."""
        WorkflowClass = get_workflow("code-review")
        workflow = WorkflowClass(multi_agent_configs=None)
        assert workflow._multi_agent_configs is None

    def test_workflow_with_multi_agent_config(self):
        """Test workflow with multi-agent config for a stage."""
        WorkflowClass = get_workflow("code-review")
        configs = {
            "analyze": {
                "agents": [{"template_id": "code_reviewer"}],
                "strategy": "parallel",
            }
        }
        workflow = WorkflowClass(multi_agent_configs=configs)
        assert workflow._multi_agent_configs is not None
        assert "analyze" in workflow._multi_agent_configs


# ===========================================================================
# Section 13: End-to-End Integration
# ===========================================================================


class TestEndToEndAgentTeamExecution:
    """End-to-end test: build team from templates, execute, check state."""

    def test_full_pipeline_with_state_persistence(self):
        """Test full Phase 1-4 pipeline: state -> agents -> team -> execute."""
        from attune.agents.state.store import AgentStateStore
        from attune.orchestration.team_builder import DynamicTeamBuilder
        from attune.orchestration.team_store import TeamSpecification

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Phase 1: State store
            store = AgentStateStore(storage_dir=tmp_dir)

            # Phase 3: Build team from templates with state store
            builder = DynamicTeamBuilder(state_store=store)
            spec = TeamSpecification(
                name="e2e-team",
                agents=[
                    {"template_id": "code_reviewer"},
                    {"template_id": "test_coverage_analyzer"},
                ],
                strategy="parallel",
                quality_gates={"min_score": 0},
            )
            team = builder.build_from_spec(spec)

            # Execute team
            result = asyncio.run(team.execute({"task": "e2e test"}))

            # Verify team result
            assert result.team_name == "e2e-team"
            assert len(result.agent_results) == 2
            assert result.execution_time_ms > 0

            # Phase 1: Verify state was persisted for each agent
            all_agents = store.get_all_agents()
            assert len(all_agents) >= 2

    def test_team_result_aggregation(self):
        """Test that team results correctly aggregate costs and times."""
        from attune.orchestration.team_builder import DynamicTeamBuilder
        from attune.orchestration.team_store import TeamSpecification

        builder = DynamicTeamBuilder()
        spec = TeamSpecification(
            name="agg-test",
            agents=[
                {"template_id": "generic_agent"},
                {"template_id": "generic_agent"},
                {"template_id": "generic_agent"},
            ],
            strategy="parallel",
            quality_gates={},
        )
        team = builder.build_from_spec(spec)
        result = asyncio.run(team.execute({"task": "aggregation test"}))

        assert len(result.agent_results) == 3
        assert result.total_cost == sum(r.cost for r in result.agent_results)
