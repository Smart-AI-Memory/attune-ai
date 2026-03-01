"""Tier routing service for workflows.

Standalone service extracted from TierRoutingMixin. Provides tier selection
with dynamic routing strategy support and adaptive upgrades.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TierService:
    """Service for selecting model tiers for workflow stages.

    Supports static tier maps, dynamic routing strategies, and adaptive
    tier upgrades based on historical telemetry.

    Args:
        workflow_name: Name of the workflow
        stages: List of stage names
        tier_map: Static mapping of stage names to ModelTier
        routing_strategy: Optional dynamic routing strategy
        enable_adaptive: Whether to enable adaptive tier upgrades

    Example:
        >>> tier_svc = TierService("code-review", stages, tier_map)
        >>> tier = tier_svc.get_tier("analysis", input_data)

    """

    def __init__(
        self,
        workflow_name: str,
        stages: list[str],
        tier_map: dict[str, Any],
        routing_strategy: Any = None,
        enable_adaptive: bool = False,
    ) -> None:
        self._workflow_name = workflow_name
        self._stages = stages
        self._tier_map = tier_map
        self._routing_strategy = routing_strategy
        self._enable_adaptive = enable_adaptive
        self._adaptive_router: Any = None

    def get_tier(
        self,
        stage_name: str,
        input_data: dict[str, Any] | None = None,
        budget_remaining: float = 100.0,
    ) -> Any:
        """Get tier for a stage using routing strategy or static map.

        Priority:
        1. Dynamic routing strategy (if configured)
        2. Static tier_map
        3. Adaptive tier upgrade (if enabled)

        Args:
            stage_name: Name of the stage
            input_data: Current workflow data
            budget_remaining: Remaining budget in USD

        Returns:
            ModelTier to use for this stage

        """
        from ..compat import ModelTier

        input_data = input_data or {}

        if self._routing_strategy is not None:
            base_tier = self._route_dynamically(stage_name, input_data, budget_remaining)
        else:
            base_tier = self._tier_map.get(stage_name, ModelTier.CAPABLE)

        if self._enable_adaptive:
            return self._check_adaptive_upgrade(stage_name, base_tier)

        return base_tier

    def get_static_tier(self, stage_name: str) -> Any:
        """Get the static tier for a stage from tier_map.

        Args:
            stage_name: Name of the stage

        Returns:
            ModelTier from tier_map, defaults to CAPABLE

        """
        from ..compat import ModelTier

        return self._tier_map.get(stage_name, ModelTier.CAPABLE)

    def _route_dynamically(
        self,
        stage_name: str,
        input_data: dict[str, Any],
        budget_remaining: float,
    ) -> Any:
        """Route using dynamic strategy."""
        from ..routing import RoutingContext

        input_size = self._estimate_input_tokens(input_data)
        complexity = self._assess_complexity(input_data)

        stage_index = self._stages.index(stage_name) if stage_name in self._stages else 0
        if stage_index == 0:
            latency_sensitivity = "high"
        elif stage_index < len(self._stages) // 2:
            latency_sensitivity = "medium"
        else:
            latency_sensitivity = "low"

        context = RoutingContext(
            task_type=f"{self._workflow_name}:{stage_name}",
            input_size=input_size,
            complexity=complexity,
            budget_remaining=budget_remaining,
            latency_sensitivity=latency_sensitivity,
        )

        return self._routing_strategy.route(context)

    def _assess_complexity(self, input_data: dict[str, Any]) -> str:
        """Assess task complexity based on stages and input."""
        from ..compat import ModelTier

        num_stages = len(self._stages)
        premium_stages = sum(1 for s in self._stages if self._tier_map.get(s) == ModelTier.PREMIUM)

        if num_stages <= 2 and premium_stages == 0:
            return "simple"
        if num_stages <= 4 and premium_stages <= 1:
            return "moderate"
        return "complex"

    def _estimate_input_tokens(self, input_data: dict[str, Any]) -> int:
        """Estimate input token count from data (~4 chars per token)."""
        try:
            data_str = json.dumps(input_data, default=str)
            return len(data_str) // 4
        except (TypeError, ValueError):
            return 1000

    def _check_adaptive_upgrade(self, stage_name: str, current_tier: Any) -> Any:
        """Check if adaptive routing recommends a tier upgrade."""
        from ..compat import ModelTier

        router = self._get_adaptive_router()
        if router is None:
            return current_tier

        should_upgrade, reason = router.recommend_tier_upgrade(
            workflow=self._workflow_name,
            stage=stage_name,
        )

        if should_upgrade:
            if current_tier == ModelTier.CHEAP:
                new_tier = ModelTier.CAPABLE
            elif current_tier == ModelTier.CAPABLE:
                new_tier = ModelTier.PREMIUM
            else:
                new_tier = current_tier

            logger.warning(
                f"Adaptive tier upgrade: {self._workflow_name}:{stage_name} "
                f"{current_tier.value} -> {new_tier.value} ({reason})",
            )
            return new_tier

        return current_tier

    def _get_adaptive_router(self) -> Any:
        """Get or create AdaptiveModelRouter (lazy init)."""
        if not self._enable_adaptive:
            return None

        if self._adaptive_router is None:
            try:
                from attune.models import AdaptiveModelRouter
                from attune.telemetry import UsageTracker

                self._adaptive_router = AdaptiveModelRouter(telemetry=UsageTracker.get_instance())
            except (ImportError, AttributeError, OSError) as e:
                logger.debug(f"Adaptive routing unavailable: {e}")
                self._enable_adaptive = False

        return self._adaptive_router
