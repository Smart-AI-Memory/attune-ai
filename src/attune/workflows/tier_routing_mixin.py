"""Tier Routing Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides tier selection with dynamic routing strategy support.

Expected attributes on the host class:
    name (str): Workflow name
    stages (list[str]): Stage names
    _routing_strategy (TierRoutingStrategy | None): Routing strategy
    _enable_adaptive_routing (bool): Whether adaptive routing is enabled
    get_tier_for_stage(stage_name): Returns static tier for a stage
    _assess_complexity(input_data): Returns complexity string (from LLMMixin)
    _check_adaptive_tier_upgrade(stage_name, tier): Returns upgraded tier (from CoordinationMixin)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .compat import ModelTier


class TierRoutingMixin:
    """Mixin providing tier routing logic for workflow stages."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    stages: list[str]
    _routing_strategy: Any  # TierRoutingStrategy | None
    _enable_adaptive_routing: bool

    def _get_tier_with_routing(
        self,
        stage_name: str,
        input_data: dict[str, Any],
        budget_remaining: float = 100.0,
    ) -> ModelTier:
        """Get tier for a stage using routing strategy or adaptive routing if available.

        Priority order:
        1. If routing_strategy configured, uses that for tier selection
        2. Otherwise uses static tier_map
        3. If adaptive routing enabled, checks for tier upgrade recommendations

        Args:
            stage_name: Name of the stage
            input_data: Current workflow data (used to estimate input size)
            budget_remaining: Remaining budget in USD for this execution

        Returns:
            ModelTier to use for this stage (potentially upgraded by adaptive routing)
        """
        # Get base tier from routing strategy or static map
        if self._routing_strategy is not None:
            from .routing import RoutingContext

            # Estimate input size from data
            input_size = self._estimate_input_tokens(input_data)

            # Assess complexity
            complexity = self._assess_complexity(input_data)

            # Determine latency sensitivity based on stage position
            # First stages are more latency-sensitive (user waiting)
            stage_index = self.stages.index(stage_name) if stage_name in self.stages else 0
            if stage_index == 0:
                latency_sensitivity = "high"
            elif stage_index < len(self.stages) // 2:
                latency_sensitivity = "medium"
            else:
                latency_sensitivity = "low"

            # Create routing context
            context = RoutingContext(
                task_type=f"{self.name}:{stage_name}",
                input_size=input_size,
                complexity=complexity,
                budget_remaining=budget_remaining,
                latency_sensitivity=latency_sensitivity,
            )

            # Delegate to routing strategy
            base_tier = self._routing_strategy.route(context)
        else:
            # Use static tier_map
            base_tier = self.get_tier_for_stage(stage_name)

        # Check if adaptive routing recommends a tier upgrade
        # This uses telemetry history to detect high failure rates
        if self._enable_adaptive_routing:
            final_tier = self._check_adaptive_tier_upgrade(stage_name, base_tier)
            return final_tier

        return base_tier

    def _estimate_input_tokens(self, input_data: dict[str, Any]) -> int:
        """Estimate input token count from data.

        Simple heuristic: ~4 characters per token on average.

        Args:
            input_data: Workflow input data

        Returns:
            Estimated token count
        """
        try:
            # Serialize to estimate size
            data_str = json.dumps(input_data, default=str)
            return len(data_str) // 4
        except (TypeError, ValueError):
            return 1000  # Default estimate
