"""Cost tracking mixin for workflow classes.

This module provides methods for calculating and reporting workflow costs,
including tier-based pricing, baseline comparisons, and cache savings.

Extracted from base.py for improved maintainability and import performance.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_classes import CostReport


class CostTrackingMixin:
    """Mixin providing cost tracking capabilities for workflows.

    This mixin adds methods for calculating costs, baseline comparisons,
    and generating cost reports with cache savings.

    Methods:
        _calculate_cost: Calculate cost for a stage based on tier and tokens
        _calculate_baseline_cost: Calculate premium-tier baseline cost
        _generate_cost_report: Generate comprehensive cost report

    Note:
        This mixin expects the class to have:
        - _stages_run: list[WorkflowStage] - stages executed in workflow
        - _get_cache_stats(): method returning cache statistics dict
        - ModelTier enum available

    """

    # These will be provided by the main class
    _stages_run: list[Any]

    def _calculate_cost(self, tier: Any, input_tokens: int, output_tokens: int) -> float:
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

    def _calculate_baseline_cost(self, input_tokens: int, output_tokens: int) -> float:
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

    def _generate_cost_report(self) -> CostReport:
        """Generate cost report from completed stages.

        Calculates total costs, baseline comparisons, savings percentages,
        and includes cache performance metrics.

        Returns:
            CostReport with comprehensive cost breakdown and savings analysis

        """
        from .data_classes import CostReport

        total_cost = 0.0
        baseline_cost = 0.0
        by_stage: dict[str, float] = {}
        by_tier: dict[str, float] = {}

        for stage in self._stages_run:
            if stage.skipped:
                continue

            total_cost += stage.cost
            by_stage[stage.name] = stage.cost

            tier_name = stage.tier.value
            by_tier[tier_name] = by_tier.get(tier_name, 0.0) + stage.cost

            # Calculate what this would cost at premium tier
            baseline_cost += self._calculate_baseline_cost(stage.input_tokens, stage.output_tokens)

        savings = baseline_cost - total_cost
        savings_percent = (savings / baseline_cost * 100) if baseline_cost > 0 else 0.0

        # Calculate cache metrics using CachingMixin
        cache_stats = self._get_cache_stats()
        cache_hits = cache_stats["hits"]
        cache_misses = cache_stats["misses"]
        cache_hit_rate = cache_stats["hit_rate"]
        estimated_cost_without_cache = total_cost
        savings_from_cache = 0.0

        # Estimate cost without cache (assumes cache hits would have incurred full cost)
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
        """Get cache statistics. Override in subclass or mixin."""
        # Default implementation - CachingMixin provides the real one
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}
