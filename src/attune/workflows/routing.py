"""Tier routing strategies for workflow execution.

Provides pluggable routing algorithms to determine which model tier
should handle each workflow stage.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.workflows.base import ModelTier


@dataclass
class RoutingContext:
    """Context information for routing decisions.

    Attributes:
        task_type: Type of task (analyze, generate, review, etc.)
        input_size: Estimated input tokens
        complexity: Task complexity (simple, moderate, complex)
        budget_remaining: Remaining budget in USD
        latency_sensitivity: Latency requirements (low, medium, high)
    """

    task_type: str
    input_size: int
    complexity: str  # "simple" | "moderate" | "complex"
    budget_remaining: float
    latency_sensitivity: str  # "low" | "medium" | "high"


class TierRoutingStrategy(ABC):
    """Abstract base class for tier routing strategies.

    Subclasses implement different routing algorithms:
    - CostOptimizedRouting: Minimize cost
    - PerformanceOptimizedRouting: Minimize latency
    - BalancedRouting: Balance cost and performance
    - HybridRouting: User-configured tier mappings
    """

    @abstractmethod
    def route(self, context: RoutingContext) -> ModelTier:
        """Route task to appropriate tier.

        Args:
            context: Routing context with task information

        Returns:
            ModelTier to use for this task
        """
        pass

    @abstractmethod
    def can_fallback(self, tier: ModelTier) -> bool:
        """Whether fallback to cheaper tier is allowed.

        Args:
            tier: The tier that failed or exceeded budget

        Returns:
            True if fallback is allowed, False otherwise
        """
        pass


class CostOptimizedRouting(TierRoutingStrategy):
    """Route to cheapest tier that can handle the task.

    Default strategy. Prioritizes cost savings over speed.

    Example:
        >>> strategy = CostOptimizedRouting()
        >>> tier = strategy.route(context)  # CHEAP for simple tasks
    """

    def route(self, context: RoutingContext) -> ModelTier:
        """Route based on task complexity, preferring cheaper tiers."""
        from attune.workflows.base import ModelTier

        if context.complexity == "simple":
            return ModelTier.CHEAP
        elif context.complexity == "complex":
            return ModelTier.PREMIUM
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        """Allow fallback except for CHEAP tier."""
        from attune.workflows.base import ModelTier

        return tier != ModelTier.CHEAP


class PerformanceOptimizedRouting(TierRoutingStrategy):
    """Route to fastest tier regardless of cost.

    Use for latency-sensitive workflows like interactive tools.

    Example:
        >>> strategy = PerformanceOptimizedRouting()
        >>> tier = strategy.route(context)  # PREMIUM for high latency sensitivity
    """

    def route(self, context: RoutingContext) -> ModelTier:
        """Route based on latency requirements."""
        from attune.workflows.base import ModelTier

        if context.latency_sensitivity == "high":
            return ModelTier.PREMIUM
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        """Never fallback - performance is priority."""
        return False


class BalancedRouting(TierRoutingStrategy):
    """Balance cost and performance with budget awareness.

    Adjusts tier selection based on remaining budget and task complexity.

    Example:
        >>> strategy = BalancedRouting(total_budget=50.0)
        >>> tier = strategy.route(context)  # Adapts based on budget
    """

    def __init__(self, total_budget: float):
        """Initialize with total budget.

        Args:
            total_budget: Total budget in USD for this workflow execution

        Raises:
            ValueError: If total_budget is not positive
        """
        if total_budget <= 0:
            raise ValueError("total_budget must be positive")
        self.total_budget = total_budget

    def route(self, context: RoutingContext) -> ModelTier:
        """Route based on budget ratio and complexity."""
        from attune.workflows.base import ModelTier

        budget_ratio = context.budget_remaining / self.total_budget

        # Low budget - use cheap tier
        if budget_ratio < 0.2:
            return ModelTier.CHEAP

        # High budget + complex task - use premium
        if budget_ratio > 0.7 and context.complexity == "complex":
            return ModelTier.PREMIUM

        # Default to capable
        return ModelTier.CAPABLE

    def can_fallback(self, tier: ModelTier) -> bool:
        """Allow fallback when budget-constrained."""
        return True
