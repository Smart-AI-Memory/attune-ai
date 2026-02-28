"""Unit tests for DynamicAgentCreator.

Tests cover:
- Agent creation from rules and responses
- Conditional agent creation based on form responses
- Agent configuration mapping
- Statistics tracking
- Helper functions (grouping, cost estimation, dependency validation)

Created: 2026-01-17
"""

from attune.meta_workflows.agent_creator import (
    DynamicAgentCreator,
    estimate_agent_costs,
    group_agents_by_tier_strategy,
    validate_agent_dependencies,
)
from attune.meta_workflows.models import (
    AgentCompositionRule,
    AgentSpec,
    FormResponse,
    FormSchema,
    MetaWorkflowTemplate,
    TierStrategy,
)


class TestDynamicAgentCreator:
    """Test DynamicAgentCreator."""

    def test_create_agents_with_no_rules(self):
        """Test creation with template that has no rules."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[],
        )

        response = FormResponse(template_id="test", responses={})

        agents = creator.create_agents(template, response)

        assert len(agents) == 0

    def test_create_agent_when_conditions_met(self):
        """Test agent is created when conditions match."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="test_runner",
                    base_template="test_coverage_analyzer",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["pytest"],
                    required_responses={"has_tests": "Yes"},
                ),
            ],
        )

        response = FormResponse(template_id="test", responses={"has_tests": "Yes"})

        agents = creator.create_agents(template, response)

        assert len(agents) == 1
        assert agents[0].role == "test_runner"
        assert agents[0].tier_strategy == TierStrategy.CHEAP_ONLY
        assert "pytest" in agents[0].tools

    def test_skip_agent_when_conditions_not_met(self):
        """Test agent is not created when conditions don't match."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="test_runner",
                    base_template="test_coverage_analyzer",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["pytest"],
                    required_responses={"has_tests": "Yes"},
                ),
            ],
        )

        response = FormResponse(template_id="test", responses={"has_tests": "No"})

        agents = creator.create_agents(template, response)

        assert len(agents) == 0

    def test_create_multiple_agents(self):
        """Test creating multiple agents from multiple rules."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="test_runner",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["pytest"],
                    required_responses={"has_tests": "Yes"},
                ),
                AgentCompositionRule(
                    role="linter",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["ruff"],
                    required_responses={"quality_checks": "Linting (ruff)"},
                ),
                AgentCompositionRule(
                    role="security_auditor",
                    base_template="security_auditor",
                    tier_strategy=TierStrategy.PROGRESSIVE,
                    tools=["bandit"],
                    required_responses={"quality_checks": "Security scan (bandit)"},
                ),
            ],
        )

        response = FormResponse(
            template_id="test",
            responses={
                "has_tests": "Yes",
                "quality_checks": ["Linting (ruff)", "Security scan (bandit)"],
            },
        )

        agents = creator.create_agents(template, response)

        assert len(agents) == 3
        roles = {agent.role for agent in agents}
        assert "test_runner" in roles
        assert "linter" in roles
        assert "security_auditor" in roles

    def test_agent_config_mapped_from_responses(self):
        """Test agent config is populated from form responses."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="version_manager",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["git"],
                    config_mapping={"version_bump": "bump_type"},
                ),
            ],
        )

        response = FormResponse(template_id="test", responses={"version_bump": "minor"})

        agents = creator.create_agents(template, response)

        assert len(agents) == 1
        assert agents[0].config["bump_type"] == "minor"

    def test_creation_stats_tracking(self):
        """Test creation statistics are tracked."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="agent1",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    required_responses={"q1": "Yes"},
                ),
                AgentCompositionRule(
                    role="agent2",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    required_responses={"q2": "Yes"},
                ),
                AgentCompositionRule(
                    role="agent3",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    required_responses={"q3": "Yes"},
                ),
            ],
        )

        # Only 2 out of 3 conditions met
        response = FormResponse(
            template_id="test",
            responses={"q1": "Yes", "q2": "Yes", "q3": "No"},
        )

        creator.create_agents(template, response)

        stats = creator.get_creation_stats()
        assert stats["total_rules_evaluated"] == 3
        assert stats["agents_created"] == 2
        assert stats["rules_skipped"] == 1

    def test_reset_stats(self):
        """Test stats can be reset."""
        creator = DynamicAgentCreator()

        template = MetaWorkflowTemplate(
            template_id="test",
            name="Test",
            description="Test",
            form_schema=FormSchema(questions=[], title="Test", description="Test"),
            agent_composition_rules=[
                AgentCompositionRule(
                    role="agent1",
                    base_template="generic",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                ),
            ],
        )

        response = FormResponse(template_id="test", responses={})

        creator.create_agents(template, response)

        # Stats should be non-zero
        assert creator.get_creation_stats()["total_rules_evaluated"] > 0

        # Reset
        creator.reset_stats()

        # Stats should be zero
        stats = creator.get_creation_stats()
        assert stats["total_rules_evaluated"] == 0
        assert stats["agents_created"] == 0
        assert stats["rules_skipped"] == 0


class TestGroupAgentsByTierStrategy:
    """Test grouping agents by tier strategy."""

    def test_group_single_tier(self):
        """Test grouping with all agents same tier."""
        agents = [
            AgentSpec(
                role="agent1",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="agent2",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        grouped = group_agents_by_tier_strategy(agents)

        assert len(grouped) == 1
        assert TierStrategy.CHEAP_ONLY in grouped
        assert len(grouped[TierStrategy.CHEAP_ONLY]) == 2

    def test_group_multiple_tiers(self):
        """Test grouping with agents in different tiers."""
        agents = [
            AgentSpec(
                role="agent1",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="agent2",
                base_template="generic",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
            AgentSpec(
                role="agent3",
                base_template="generic",
                tier_strategy=TierStrategy.CAPABLE_FIRST,
            ),
            AgentSpec(
                role="agent4",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        grouped = group_agents_by_tier_strategy(agents)

        assert len(grouped) == 3
        assert len(grouped[TierStrategy.CHEAP_ONLY]) == 2
        assert len(grouped[TierStrategy.PROGRESSIVE]) == 1
        assert len(grouped[TierStrategy.CAPABLE_FIRST]) == 1

    def test_group_empty_list(self):
        """Test grouping with empty list."""
        grouped = group_agents_by_tier_strategy([])

        assert len(grouped) == 0


class TestEstimateAgentCosts:
    """Test cost estimation."""

    def test_estimate_with_default_costs(self):
        """Test estimation with default cost mapping."""
        agents = [
            AgentSpec(
                role="agent1",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="agent2",
                base_template="generic",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
        ]

        estimate = estimate_agent_costs(agents)

        assert "total_estimated_cost" in estimate
        assert "by_tier" in estimate
        assert "agent_count" in estimate
        assert estimate["agent_count"] == 2
        assert estimate["total_estimated_cost"] > 0

    def test_estimate_with_custom_costs(self):
        """Test estimation with custom cost mapping."""
        agents = [
            AgentSpec(
                role="agent1",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        custom_costs = {"cheap_only": 0.10}

        estimate = estimate_agent_costs(agents, cost_per_tier=custom_costs)

        assert estimate["total_estimated_cost"] == 0.10
        assert estimate["by_tier"]["cheap_only"] == 0.10

    def test_estimate_multiple_agents_same_tier(self):
        """Test estimation with multiple agents in same tier."""
        agents = [
            AgentSpec(
                role="agent1",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="agent2",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="agent3",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        estimate = estimate_agent_costs(agents)

        # 3 cheap_only agents × $0.05 = $0.15
        assert estimate["total_estimated_cost"] == 0.15
        assert estimate["by_tier"]["cheap_only"] == 0.15


class TestValidateAgentDependencies:
    """Test agent dependency validation."""

    def test_no_warnings_when_dependencies_met(self):
        """Test no warnings when all dependencies satisfied."""
        agents = [
            AgentSpec(
                role="package_builder",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="publisher",
                base_template="generic",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
        ]

        warnings = validate_agent_dependencies(agents)

        assert len(warnings) == 0

    def test_warning_when_publisher_without_builder(self):
        """Test warning when publisher present but package_builder missing."""
        agents = [
            AgentSpec(
                role="publisher",
                base_template="generic",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
        ]

        warnings = validate_agent_dependencies(agents)

        assert len(warnings) == 1
        assert "publisher" in warnings[0]
        assert "package_builder" in warnings[0]

    def test_warning_when_changelog_updater_without_version_manager(self):
        """Test warning when changelog_updater present but version_manager missing."""
        agents = [
            AgentSpec(
                role="changelog_updater",
                base_template="generic",
                tier_strategy=TierStrategy.CAPABLE_FIRST,
            ),
        ]

        warnings = validate_agent_dependencies(agents)

        assert len(warnings) == 1
        assert "changelog_updater" in warnings[0]
        assert "version_manager" in warnings[0]

    def test_multiple_dependency_warnings(self):
        """Test multiple dependency warnings."""
        agents = [
            AgentSpec(
                role="publisher",
                base_template="generic",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
            AgentSpec(
                role="changelog_updater",
                base_template="generic",
                tier_strategy=TierStrategy.CAPABLE_FIRST,
            ),
        ]

        warnings = validate_agent_dependencies(agents)

        assert len(warnings) == 2

    def test_no_warnings_for_agents_without_dependencies(self):
        """Test no warnings for agents that don't have dependencies."""
        agents = [
            AgentSpec(
                role="test_runner",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
            AgentSpec(
                role="linter",
                base_template="generic",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        warnings = validate_agent_dependencies(agents)

        assert len(warnings) == 0
