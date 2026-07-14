"""Execution strategies for agent composition patterns.

This submodule implements the grammar rules for composing agents:
1. Sequential (A → B → C)
2. Parallel (A || B || C)
3. Debate (A ⇄ B ⇄ C → Synthesis)
4. Teaching (Junior → Expert validation)
5. Refinement (Draft → Review → Polish)
6. Adaptive (Classifier → Specialist)
7. Conditional (if X then A else B) - branching based on gates

This package provides modular organization of execution strategies:
- data_classes: AgentResult, StrategyResult
- conditions: ConditionType, Condition, Branch, ConditionEvaluator
- nesting: WorkflowReference, InlineWorkflow, NestingContext, WorkflowDefinition
- base: ExecutionStrategy ABC
- core_strategies: Sequential, Parallel, Debate, Teaching, Refinement, Adaptive
- conditional_strategies: Conditional, MultiConditional, Nested, NestedSequential
- advanced: ToolEnhanced, PromptCached, etc.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# Base strategy class
from .base import ExecutionStrategy

# Conditional and nested strategies
from .conditional_strategies import (
    ConditionalStrategy,
    MultiConditionalStrategy,
    NestedSequentialStrategy,
    NestedStrategy,
    StepDefinition,
)

# Condition types and evaluator
from .conditions import Branch, Condition, ConditionEvaluator, ConditionType

# Core strategies
from .core_strategies import (
    AdaptiveStrategy,
    DebateStrategy,
    ParallelStrategy,
    RefinementStrategy,
    SequentialStrategy,
    TeachingStrategy,
)

# Data classes
from .data_classes import AgentResult, StrategyResult

# Nesting support
from .nesting import (
    WORKFLOW_REGISTRY,
    InlineWorkflow,
    NestingContext,
    WorkflowDefinition,
    WorkflowReference,
    get_workflow,
    register_workflow,
)

# Strategy registry for lookup by name (partial - advanced strategies added in main module)
_STRATEGY_REGISTRY: dict[str, type[ExecutionStrategy]] = {
    # Core patterns (1-6)
    "sequential": SequentialStrategy,
    "parallel": ParallelStrategy,
    "debate": DebateStrategy,
    "teaching": TeachingStrategy,
    "refinement": RefinementStrategy,
    "adaptive": AdaptiveStrategy,
    # Conditional patterns (7+)
    "conditional": ConditionalStrategy,
    "multi_conditional": MultiConditionalStrategy,
    "nested": NestedStrategy,
    "nested_sequential": NestedSequentialStrategy,
}


def get_strategy(strategy_name: str) -> ExecutionStrategy:
    """Get strategy instance by name.

    Args:
        strategy_name: Strategy name (e.g., "sequential", "parallel")

    Returns:
        ExecutionStrategy instance

    Raises:
        ValueError: If strategy name is invalid

    Example:
        >>> strategy = get_strategy("sequential")
        >>> isinstance(strategy, SequentialStrategy)
        True

    """
    if strategy_name not in _STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. Available: {list(_STRATEGY_REGISTRY.keys())}",
        )

    strategy_class = _STRATEGY_REGISTRY[strategy_name]
    return strategy_class()


def register_strategy(name: str, strategy_class: type[ExecutionStrategy]) -> None:
    """Register a strategy class by name.

    Used by main module to add advanced strategies.

    Args:
        name: Strategy name
        strategy_class: Strategy class

    """
    _STRATEGY_REGISTRY[name] = strategy_class


__all__ = [
    # Data classes
    "AgentResult",
    "StrategyResult",
    # Conditions
    "Branch",
    "Condition",
    "ConditionEvaluator",
    "ConditionType",
    # Nesting
    "InlineWorkflow",
    "NestingContext",
    "WORKFLOW_REGISTRY",
    "WorkflowDefinition",
    "WorkflowReference",
    "get_workflow",
    "register_workflow",
    # Base strategy
    "ExecutionStrategy",
    # Core strategies
    "AdaptiveStrategy",
    "DebateStrategy",
    "ParallelStrategy",
    "RefinementStrategy",
    "SequentialStrategy",
    "TeachingStrategy",
    # Conditional strategies
    "ConditionalStrategy",
    "MultiConditionalStrategy",
    "NestedSequentialStrategy",
    "NestedStrategy",
    "StepDefinition",
    # Functions
    "get_strategy",
    "register_strategy",
]
