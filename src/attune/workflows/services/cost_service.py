"""Cost tracking service for workflows.

Standalone service extracted from CostTrackingMixin. Calculates stage costs,
baseline comparisons, and generates cost reports with cache savings.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..data_classes import CostReport, WorkflowStage

logger = logging.getLogger(__name__)


class CostService:
    """Service for calculating and reporting workflow costs.

    Provides tier-based pricing, baseline comparisons, and cache savings analysis.

    Args:
        cache_stats_fn: Optional callable returning cache stats dict.
            Expected signature: () -> {"hits": int, "misses": int, "hit_rate": float}

    Example:
        >>> cost_svc = CostService()
        >>> cost = cost_svc.calculate_cost(tier, input_tokens=500, output_tokens=200)
        >>> report = cost_svc.generate_report(stages_run)

    """

    def __init__(
        self,
        cache_stats_fn: Any = None,
    ) -> None:
        """Initialize CostService for tracking workflow costs.

        Args:
            cache_stats_fn: Optional callable returning cache hit/miss stats.

        """
        self._cache_stats_fn = cache_stats_fn

    def calculate_cost(self, tier: Any, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a stage.

        Args:
            tier: ModelTier enum value for the stage
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated

        Returns:
            Total cost in dollars for this stage

        """
        from attune.cost_tracker import MODEL_PRICING

        tier_name = tier.value
        pricing = MODEL_PRICING.get(tier_name, MODEL_PRICING["capable"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def calculate_baseline_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate what the cost would be using premium tier.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated

        Returns:
            Cost in dollars if premium tier was used

        """
        from attune.cost_tracker import MODEL_PRICING

        pricing = MODEL_PRICING["premium"]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def generate_report(self, stages_run: list[WorkflowStage]) -> CostReport:
        """Generate cost report from completed stages.

        Calculates total costs, baseline comparisons, savings percentages,
        and includes cache performance metrics.

        Args:
            stages_run: List of completed workflow stages

        Returns:
            CostReport with comprehensive cost breakdown and savings analysis

        """
        from ..data_classes import CostReport

        total_cost = 0.0
        baseline_cost = 0.0
        by_stage: dict[str, float] = {}
        by_tier: dict[str, float] = {}

        for stage in stages_run:
            if stage.skipped:
                continue

            total_cost += stage.cost
            by_stage[stage.name] = stage.cost

            tier_name = stage.tier.value
            by_tier[tier_name] = by_tier.get(tier_name, 0.0) + stage.cost

            baseline_cost += self.calculate_baseline_cost(stage.input_tokens, stage.output_tokens)

        savings = baseline_cost - total_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        # Calculate cache metrics
        cache_stats = self._get_cache_stats()
        cache_hits = cache_stats["hits"]
        cache_misses = cache_stats["misses"]
        cache_hit_rate = cache_stats["hit_rate"]
        estimated_cost_without_cache = total_cost
        savings_from_cache = 0.0

        if cache_hits > 0:
            avg_cost_per_call = total_cost / cache_misses if cache_misses > 0 else 0.0
            estimated_additional_cost = cache_hits * avg_cost_per_call
            estimated_cost_without_cache = total_cost + estimated_additional_cost
            savings_from_cache = estimated_additional_cost

        return CostReport(
            total_cost=total_cost,
            baseline_cost=baseline_cost,
            savings=savings,
            savings_percent=savings_percent,
            by_stage=by_stage,
            by_tier=by_tier,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            cache_hit_rate=cache_hit_rate,
            estimated_cost_without_cache=estimated_cost_without_cache,
            savings_from_cache=savings_from_cache,
        )

    def _get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for cost reporting."""
        if self._cache_stats_fn is not None:
            try:
                return self._cache_stats_fn()
            except (AttributeError, TypeError) as e:
                logger.debug(f"Cache stats not available: {e}")
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}
