"""Dynamic agent creator from templates and form responses.

Generates agent specifications based on template rules and user's
form responses. Core of the meta-workflow system's agent composition.

Created: 2026-01-17
Purpose: Dynamic agent team generation
"""

import logging
from typing import Any

from attune.meta_workflows.models import (
    AgentCompositionRule,
    AgentSpec,
    FormResponse,
    MetaWorkflowTemplate,
    TierStrategy,
)

logger = logging.getLogger(__name__)


class DynamicAgentCreator:
    """Creates agent teams dynamically from templates and form responses.

    Takes a meta-workflow template and user's form responses, then generates
    a list of agent specifications based on the template's composition rules.
    """

    def __init__(self):
        """Initialize the dynamic agent creator."""
        self.creation_stats: dict[str, int] = {
            "total_rules_evaluated": 0,
            "agents_created": 0,
            "rules_skipped": 0,
        }

    def create_agents(
        self,
        template: MetaWorkflowTemplate,
        form_response: FormResponse,
    ) -> list[AgentSpec]:
        """Create agents from template rules and form responses.

        Args:
            template: Meta-workflow template with composition rules
            form_response: User's responses to form questions

        Returns:
            List of AgentSpec instances to execute

        Raises:
            ValueError: If template or form_response is invalid

        """
        if not template.agent_composition_rules:
            logger.warning(f"Template {template.template_id} has no composition rules")
            return []

        agents = []
        self.creation_stats["total_rules_evaluated"] = len(template.agent_composition_rules)

        logger.info(f"Evaluating {len(template.agent_composition_rules)} composition rules")

        for rule in template.agent_composition_rules:
            # Check if agent should be created based on form responses
            if rule.should_create(form_response):
                agent = self._create_agent_from_rule(rule, form_response)
                agents.append(agent)
                self.creation_stats["agents_created"] += 1

                logger.debug(
                    f"Created agent: {agent.role} "
                    f"(tier: {agent.tier_strategy.value}, id: {agent.agent_id})",
                )
            else:
                self.creation_stats["rules_skipped"] += 1
                logger.debug(f"Skipped agent {rule.role} - conditions not met")

        logger.info(
            f"Created {len(agents)} agents from {len(template.agent_composition_rules)} rules",
        )

        return agents

    def _create_agent_from_rule(
        self,
        rule: AgentCompositionRule,
        form_response: FormResponse,
    ) -> AgentSpec:
        """Create an AgentSpec from a composition rule and form responses.

        Args:
            rule: Agent composition rule
            form_response: User's form responses

        Returns:
            AgentSpec instance configured for execution

        """
        # Map config from form responses
        config = rule.create_agent_config(form_response)

        # Create agent spec
        agent = AgentSpec(
            role=rule.role,
            base_template=rule.base_template,
            tier_strategy=rule.tier_strategy,
            tools=rule.tools.copy(),  # Copy to avoid mutation
            config=config,
            success_criteria=rule.success_criteria.copy(),  # Copy to avoid mutation
        )

        return agent

    def get_creation_stats(self) -> dict[str, int]:
        """Get statistics about agent creation.

        Returns:
            Dictionary with creation statistics

        """
        return self.creation_stats.copy()

    def reset_stats(self) -> None:
        """Reset creation statistics."""
        self.creation_stats = {
            "total_rules_evaluated": 0,
            "agents_created": 0,
            "rules_skipped": 0,
        }
        logger.debug("Agent creation stats reset")


# =============================================================================
# Helper functions for agent composition
# =============================================================================


def group_agents_by_tier_strategy(
    agents: list[AgentSpec],
) -> dict[TierStrategy, list[AgentSpec]]:
    """Group agents by their tier strategy.

    Useful for execution planning (e.g., run all cheap_only agents first).

    Args:
        agents: List of agent specs

    Returns:
        Dictionary mapping TierStrategy → list of agents

    Example:
        >>> agents = [
        ...     AgentSpec(role="test", base_template="generic", tier_strategy=TierStrategy.CHEAP_ONLY),
        ...     AgentSpec(role="review", base_template="generic", tier_strategy=TierStrategy.PROGRESSIVE),
        ... ]
        >>> grouped = group_agents_by_tier_strategy(agents)
        >>> len(grouped[TierStrategy.CHEAP_ONLY])
        1

    """
    grouped: dict[TierStrategy, list[AgentSpec]] = {}

    for agent in agents:
        if agent.tier_strategy not in grouped:
            grouped[agent.tier_strategy] = []
        grouped[agent.tier_strategy].append(agent)

    return grouped


def estimate_agent_costs(
    agents: list[AgentSpec],
    cost_per_tier: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Estimate total cost for executing agents.

    Args:
        agents: List of agent specs
        cost_per_tier: Optional cost mapping (tier → estimated cost)
                      Defaults to reasonable estimates

    Returns:
        Dictionary with cost estimates

    Example:
        >>> agents = [AgentSpec(role="test", base_template="generic", tier_strategy=TierStrategy.CHEAP_ONLY)]
        >>> estimate_agent_costs(agents)
        {'total_estimated_cost': 0.05, 'by_tier': {'cheap_only': 0.05}, 'agent_count': 1}

    """
    if cost_per_tier is None:
        # Default cost estimates per tier strategy
        cost_per_tier = {
            "cheap_only": 0.05,
            "progressive": 0.15,  # Average, might escalate
            "capable_first": 0.25,  # Starts higher
            "premium_only": 0.40,
        }

    total_cost = 0.0
    cost_by_tier: dict[str, float] = {}

    for agent in agents:
        tier_key = agent.tier_strategy.value
        agent_cost = cost_per_tier.get(tier_key, 0.10)  # Default fallback

        total_cost += agent_cost

        if tier_key not in cost_by_tier:
            cost_by_tier[tier_key] = 0.0
        cost_by_tier[tier_key] += agent_cost

    return {
        "total_estimated_cost": round(total_cost, 2),
        "by_tier": {k: round(v, 2) for k, v in cost_by_tier.items()},
        "agent_count": len(agents),
    }


def validate_agent_dependencies(agents: list[AgentSpec]) -> list[str]:
    """Validate that agent dependencies are satisfied.

    Checks for common dependency issues (e.g., publisher needs package_builder).

    Args:
        agents: List of agent specs

    Returns:
        List of validation warnings (empty if all OK)

    Example:
        >>> agents = [AgentSpec(role="publisher", base_template="generic", tier_strategy=TierStrategy.CHEAP_ONLY)]
        >>> warnings = validate_agent_dependencies(agents)
        >>> len(warnings) > 0  # Should warn about missing package_builder
        True

    """
    warnings = []
    agent_roles = {agent.role for agent in agents}

    # Common dependencies
    dependencies = {
        "publisher": ["package_builder"],
        "changelog_updater": ["version_manager"],
    }

    for agent in agents:
        if agent.role in dependencies:
            for required_role in dependencies[agent.role]:
                if required_role not in agent_roles:
                    warnings.append(
                        f"Agent '{agent.role}' typically requires '{required_role}' "
                        f"but it's not in the agent list",
                    )

    return warnings
