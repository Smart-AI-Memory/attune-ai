"""Smoke tests for workflows, agents, templates, and execution strategies.

Verifies that every registered workflow can be instantiated, every agent
class can be created, agent templates resolve, and the live execution
strategies load.

No API key required — agents use rule-based fallback when no LLM is available.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

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
    "bug-predict",
    "security-audit",
    "perf-audit",
    "test-gen",
    "test-gen-parallel",
    "refactor-plan",
    "dependency-check",
    "secure-release",
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

    def test_fourteen_templates_registered(self):
        """Test that 14 pre-built templates are available."""
        from attune.orchestration.agent_templates import get_all_templates

        templates = get_all_templates()
        assert len(templates) == 14

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
        assert len(cheap) + len(capable) + len(premium) == 14

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
        assert len(registry) == 14


# ===========================================================================
# Section 6: Agent Teams (production)
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


# ===========================================================================
# Section 7: Execution Strategies
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
# Section 8: State Persistence Mixin in Workflows (Phase 4a)
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
