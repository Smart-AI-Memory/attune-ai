"""Meta-orchestrator Cost and Duration Estimation.

Cost and duration estimation for agent execution plans.
Extracted from meta_orchestrator.py for maintainability.

Contains:
- EstimationMixin: Cost estimation, duration estimation

Expected attributes on the host class:
    (none - all state accessed via parameters)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from .agent_templates import AgentTemplate
from .meta_orchestrator import CompositionPattern


class EstimationMixin:
    """Mixin providing cost and duration estimation for meta-orchestrator."""

    def _estimate_cost(self, agents: list[AgentTemplate]) -> float:
        """Estimate execution cost based on agent tiers.

        Args:
            agents: List of agents

        Returns:
            Estimated cost in arbitrary units

        """
        tier_costs = {
            "CHEAP": 1.0,
            "CAPABLE": 3.0,
            "PREMIUM": 10.0,
        }

        total_cost = 0.0
        for agent in agents:
            total_cost += tier_costs.get(agent.tier_preference, 3.0)

        return total_cost

    def _estimate_duration(self, agents: list[AgentTemplate], strategy: CompositionPattern) -> int:
        """Estimate execution duration in seconds.

        Args:
            agents: List of agents
            strategy: Composition pattern

        Returns:
            Estimated duration in seconds

        """
        # Get max timeout from agents
        max_timeout = max(
            (agent.resource_requirements.timeout_seconds for agent in agents),
            default=300,
        )

        # Sequential: sum of timeouts
        if strategy == CompositionPattern.SEQUENTIAL:
            return sum(agent.resource_requirements.timeout_seconds for agent in agents)

        # Parallel: max timeout
        if strategy == CompositionPattern.PARALLEL:
            return max_timeout

        # Debate: multiple rounds, estimate 2x max timeout
        if strategy == CompositionPattern.DEBATE:
            return max_timeout * 2

        # Teaching: initial attempt + possible expert review
        if strategy == CompositionPattern.TEACHING:
            return int(max_timeout * 1.5)

        # Refinement: 3 passes (draft → review → polish)
        if strategy == CompositionPattern.REFINEMENT:
            return max_timeout * 3

        # Adaptive: classification + specialist
        if strategy == CompositionPattern.ADAPTIVE:
            return int(max_timeout * 1.2)

        # Anthropic Pattern 8: Tool-Enhanced (single agent with tools, efficient)
        if strategy == CompositionPattern.TOOL_ENHANCED:
            return max_timeout  # Similar to sequential for single agent

        # Anthropic Pattern 9: Prompt-Cached Sequential (faster with cache hits)
        if strategy == CompositionPattern.PROMPT_CACHED_SEQUENTIAL:
            # Sequential but 20% faster due to cached context reducing token processing
            total = sum(agent.resource_requirements.timeout_seconds for agent in agents)
            return int(total * 0.8)

        # Anthropic Pattern 10: Delegation Chain (coordinator + specialists in sequence)
        if strategy == CompositionPattern.DELEGATION_CHAIN:
            # Coordinator analyzes, then specialists execute (sequential-like)
            return sum(agent.resource_requirements.timeout_seconds for agent in agents)

        # Conditional: branch evaluation + selected path
        if strategy == CompositionPattern.CONDITIONAL:
            return int(max_timeout * 1.1)

        # Default: max timeout
        return max_timeout
