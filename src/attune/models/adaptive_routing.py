"""Adaptive Model Routing based on historical telemetry.

This module implements Pattern 3 from AGENT_COORDINATION_ARCHITECTURE.md:
Using telemetry history to learn which models work best for each workflow/stage.

Key Features:
- Analyzes historical performance per model/workflow/stage
- Recommends best model based on success rate and cost
- Auto-detects when tier upgrades are needed (>20% failure rate)
- Respects cost and latency constraints

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_model_registry = None


def _get_registry():
    """Get ModelRegistry instance (lazy load to avoid circular import)."""
    global _model_registry
    if _model_registry is None:
        from .registry import MODEL_REGISTRY

        _model_registry = MODEL_REGISTRY
    return _model_registry


@dataclass
class ModelPerformance:
    """Performance metrics for a model on a specific task.

    Attributes:
        model_id: Model identifier (e.g., "claude-sonnet-4.5")
        tier: Model tier (CHEAP, CAPABLE, PREMIUM)
        success_rate: Percentage of successful calls (0.0 - 1.0)
        avg_latency_ms: Average response time in milliseconds
        avg_cost: Average cost per call in USD
        sample_size: Number of calls analyzed
        recent_failures: Number of failures in last 20 calls
    """

    model_id: str
    tier: str
    success_rate: float
    avg_latency_ms: float
    avg_cost: float
    sample_size: int
    recent_failures: int = 0

    @property
    def quality_score(self) -> float:
        """Calculate quality score for ranking models.

        Score prioritizes:
        1. Success rate (most important)
        2. Cost (secondary)

        Returns:
            Quality score (higher is better)
        """
        # Success rate contributes 100 points max
        # Lower cost adds bonus points
        return (self.success_rate * 100) - (self.avg_cost * 10)


class AdaptiveModelRouter:
    """Route tasks to models based on historical telemetry performance.

    Uses telemetry data to learn which models work best for each workflow/stage
    combination. Automatically recommends tier upgrades when failure rates are high.

    Example:
        >>> from attune.telemetry import UsageTracker
        >>> router = AdaptiveModelRouter(UsageTracker.get_instance())
        >>>
        >>> # Get best model for this workflow stage
        >>> model = router.get_best_model(
        ...     workflow="code-review",
        ...     stage="analysis",
        ...     max_cost=0.01
        ... )
        >>> print(f"Using {model}")
        Using claude-haiku-4-5-20251001
        >>>
        >>> # Check if we should upgrade tier
        >>> should_upgrade, reason = router.recommend_tier_upgrade(
        ...     workflow="code-review",
        ...     stage="analysis"
        ... )
        >>> if should_upgrade:
        ...     print(f"⚠️ {reason}")
        ⚠️ High failure rate: 25.0% in last 20 calls
    """

    # Minimum sample size for making routing decisions
    MIN_SAMPLE_SIZE = 10

    # Failure rate threshold for tier upgrade recommendation
    FAILURE_RATE_THRESHOLD = 0.2  # 20%

    # Recent window size for failure detection
    RECENT_WINDOW_SIZE = 20

    def __init__(self, telemetry: Any):
        """Initialize adaptive router.

        Args:
            telemetry: UsageTracker instance for telemetry data access
        """
        self.telemetry = telemetry

    def _get_default_model(self, tier: str = "CHEAP") -> str:
        """Get default Anthropic model for a tier from registry.

        This dynamically fetches the current Anthropic model for each tier,
        so when new models are released (e.g., Claude 5), they're automatically used.

        Args:
            tier: Tier name (CHEAP, CAPABLE, or PREMIUM)

        Returns:
            Model ID from registry (e.g., "claude-haiku-4-5-20251001")
        """
        registry = _get_registry()

        # Get Anthropic model for this tier
        tier_lower = tier.lower()
        if tier_lower in registry.get("anthropic", {}):
            return registry["anthropic"][tier_lower].id

        # Fallback to known models if registry lookup fails
        fallbacks = {
            "cheap": "claude-haiku-4-5-20251001",
            "capable": "claude-sonnet-4-5-20250929",
            "premium": "claude-opus-4-6",
        }
        return fallbacks.get(tier_lower, "claude-haiku-4-5-20251001")

    def get_best_model(
        self,
        workflow: str,
        stage: str,
        max_cost: float | None = None,
        max_latency_ms: int | None = None,
        min_success_rate: float = 0.8,
    ) -> str:
        """Get best model for workflow/stage based on historical performance.

        Analyzes recent telemetry to find the model with the best quality score
        (success rate + cost efficiency) that meets the specified constraints.

        Args:
            workflow: Workflow name (e.g., "code-review", "bug-predict")
            stage: Stage name (e.g., "analysis", "synthesis")
            max_cost: Maximum acceptable cost per call (USD)
            max_latency_ms: Maximum acceptable latency (milliseconds)
            min_success_rate: Minimum acceptable success rate (0.0 - 1.0)

        Returns:
            Model ID to use (e.g., "claude-haiku-4-5-20251001")

        Example:
            >>> model = router.get_best_model(
            ...     workflow="code-review",
            ...     stage="analysis",
            ...     max_cost=0.01,
            ...     min_success_rate=0.9
            ... )
            >>> print(model)
            claude-haiku-4-5-20251001
        """
        # Get performance data for all models on this workflow/stage
        performances = self._analyze_model_performance(workflow, stage)

        if not performances:
            # No historical data, use default Anthropic cheap model from registry
            default_model = self._get_default_model("CHEAP")
            logger.info(
                "adaptive_routing_no_history",
                workflow=workflow,
                stage=stage,
                fallback=default_model,
            )
            return default_model

        # Filter by constraints
        candidates = []
        for perf in performances:
            # Skip if insufficient data
            if perf.sample_size < self.MIN_SAMPLE_SIZE:
                continue

            # Skip if doesn't meet minimum success rate
            if perf.success_rate < min_success_rate:
                continue

            # Skip if exceeds cost constraint
            if max_cost is not None and perf.avg_cost > max_cost:
                continue

            # Skip if exceeds latency constraint
            if max_latency_ms is not None and perf.avg_latency_ms > max_latency_ms:
                continue

            candidates.append(perf)

        if not candidates:
            # All models filtered out, fall back to default Anthropic model
            default_model = self._get_default_model("CHEAP")
            logger.warning(
                "adaptive_routing_no_candidates",
                workflow=workflow,
                stage=stage,
                constraints={"max_cost": max_cost, "max_latency_ms": max_latency_ms},
                fallback=default_model,
            )
            return default_model

        # Sort by quality score (success rate + cost efficiency)
        candidates.sort(key=lambda p: p.quality_score, reverse=True)
        best = candidates[0]

        logger.info(
            "adaptive_routing_selected",
            workflow=workflow,
            stage=stage,
            model=best.model_id,
            success_rate=f"{best.success_rate:.1%}",
            avg_cost=f"${best.avg_cost:.4f}",
            sample_size=best.sample_size,
        )

        return best.model_id

    def recommend_tier_upgrade(self, workflow: str, stage: str) -> tuple[bool, str]:
        """Check if tier should be upgraded based on failure rate.

        Analyzes recent telemetry (last 20 calls) for this workflow/stage.
        If failure rate exceeds threshold (20%), recommends tier upgrade.

        Args:
            workflow: Workflow name
            stage: Stage name

        Returns:
            Tuple of (should_upgrade: bool, reason: str)

        Example:
            >>> should_upgrade, reason = router.recommend_tier_upgrade(
            ...     workflow="code-review",
            ...     stage="analysis"
            ... )
            >>> if should_upgrade:
            ...     print(f"⚠️ Upgrading tier: {reason}")
            ⚠️ Upgrading tier: High failure rate: 25.0% in last 20 calls
        """
        # Get recent entries for this workflow/stage
        entries = self._get_workflow_stage_entries(workflow, stage, days=7)

        if len(entries) < self.MIN_SAMPLE_SIZE:
            return False, f"Insufficient data ({len(entries)} calls, need {self.MIN_SAMPLE_SIZE})"

        # Analyze recent window (last 20 calls)
        recent = entries[-self.RECENT_WINDOW_SIZE :]
        failures = sum(1 for e in recent if not e.get("success", True))
        failure_rate = failures / len(recent)

        if failure_rate > self.FAILURE_RATE_THRESHOLD:
            return (
                True,
                f"High failure rate: {failure_rate:.1%} ({failures}/{len(recent)} failed in recent calls)",
            )

        return False, f"Performance acceptable: {failure_rate:.1%} failure rate"

    def get_routing_stats(
        self, workflow: str, stage: str | None = None, days: int = 7
    ) -> dict[str, Any]:
        """Get routing statistics for a workflow (or specific stage).

        Args:
            workflow: Workflow name
            stage: Optional stage name (None for all stages)
            days: Number of days to analyze

        Returns:
            Dictionary with routing statistics:
            - models_used: List of models used
            - performance_by_model: Performance metrics per model
            - total_calls: Total number of calls
            - avg_cost: Average cost per call
            - avg_success_rate: Average success rate

        Example:
            >>> stats = router.get_routing_stats("code-review", days=7)
            >>> print(f"Models used: {stats['models_used']}")
            Models used: ['claude-haiku-3.5', 'claude-sonnet-4.5']
            >>> print(f"Average cost: ${stats['avg_cost']:.4f}")
            Average cost: $0.0023
        """
        entries = self._get_workflow_stage_entries(workflow, stage, days=days)

        if not entries:
            return {
                "models_used": [],
                "performance_by_model": {},
                "total_calls": 0,
                "avg_cost": 0.0,
                "avg_success_rate": 0.0,
            }

        # Calculate stats
        models_used = list({e["model"] for e in entries})
        total_calls = len(entries)
        total_cost = sum(e.get("cost", 0.0) for e in entries)
        successes = sum(1 for e in entries if e.get("success", True))

        # Per-model performance
        performance_by_model = {}
        for model in models_used:
            model_entries = [e for e in entries if e["model"] == model]
            model_successes = sum(1 for e in model_entries if e.get("success", True))

            performance_by_model[model] = {
                "calls": len(model_entries),
                "success_rate": model_successes / len(model_entries),
                "avg_cost": sum(e.get("cost", 0.0) for e in model_entries) / len(model_entries),
                "avg_latency_ms": sum(e.get("duration_ms", 0) for e in model_entries)
                / len(model_entries),
            }

        return {
            "workflow": workflow,
            "stage": stage or "all",
            "days_analyzed": days,
            "models_used": models_used,
            "performance_by_model": performance_by_model,
            "total_calls": total_calls,
            "avg_cost": total_cost / total_calls if total_calls > 0 else 0.0,
            "avg_success_rate": successes / total_calls if total_calls > 0 else 0.0,
        }

    def _analyze_model_performance(
        self, workflow: str, stage: str, days: int = 7
    ) -> list[ModelPerformance]:
        """Analyze performance of all models for this workflow/stage.

        Args:
            workflow: Workflow name
            stage: Stage name
            days: Number of days to analyze

        Returns:
            List of ModelPerformance objects, one per model
        """
        entries = self._get_workflow_stage_entries(workflow, stage, days=days)

        if not entries:
            return []

        # Group by model
        by_model: dict[str, list[dict]] = {}
        for entry in entries:
            model = entry["model"]
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(entry)

        # Calculate performance metrics per model
        performances = []
        for model, model_entries in by_model.items():
            total = len(model_entries)
            successes = sum(1 for e in model_entries if e.get("success", True))
            success_rate = successes / total

            avg_latency = sum(e.get("duration_ms", 0) for e in model_entries) / total
            avg_cost = sum(e.get("cost", 0.0) for e in model_entries) / total

            # Analyze recent failures (last 20 calls)
            recent = model_entries[-self.RECENT_WINDOW_SIZE :]
            recent_failures = sum(1 for e in recent if not e.get("success", True))

            performances.append(
                ModelPerformance(
                    model_id=model,
                    tier=model_entries[0].get("tier", "unknown"),
                    success_rate=success_rate,
                    avg_latency_ms=avg_latency,
                    avg_cost=avg_cost,
                    sample_size=total,
                    recent_failures=recent_failures,
                )
            )

        return performances

    def _get_workflow_stage_entries(
        self, workflow: str, stage: str | None, days: int
    ) -> list[dict[str, Any]]:
        """Get telemetry entries for a workflow/stage.

        Args:
            workflow: Workflow name
            stage: Stage name (None for all stages)
            days: Number of days to retrieve

        Returns:
            List of telemetry entries
        """
        # Get recent entries from telemetry tracker
        all_entries = self.telemetry.get_recent_entries(limit=10000, days=days)

        # Filter to this workflow
        workflow_entries = [e for e in all_entries if e.get("workflow") == workflow]

        # Filter to this stage if specified
        if stage is not None:
            workflow_entries = [e for e in workflow_entries if e.get("stage") == stage]

        return workflow_entries


__all__ = ["AdaptiveModelRouter", "ModelPerformance"]
