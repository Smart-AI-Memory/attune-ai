"""Execution strategies for agent composition patterns.

This module implements the 13 grammar rules for composing agents:
1. Sequential (A → B → C)
2. Parallel (A || B || C)
3. Debate (A ⇄ B ⇄ C → Synthesis)
4. Teaching (Junior → Expert validation)
5. Refinement (Draft → Review → Polish)
6. Adaptive (Classifier → Specialist)
7. Conditional (if X then A else B) - branching based on gates
8. MultiConditional (switch/case pattern)
9. Nested (recursive workflow execution)
10. NestedSequential (sequential with nested workflow support)
11. ToolEnhanced (single agent with comprehensive tools)
12. PromptCachedSequential (sequential with cached context)
13. DelegationChain (hierarchical delegation)

Security:
    - All agent outputs validated before passing to next agent
    - No eval() or exec() usage
    - Timeout enforcement at strategy level
    - Condition predicates validated (no code execution)

Example:
    >>> strategy = SequentialStrategy()
    >>> agents = [agent1, agent2, agent3]
    >>> result = await strategy.execute(agents, context)

    >>> # Conditional branching example
    >>> cond_strategy = ConditionalStrategy(
    ...     condition=Condition(predicate={"confidence": {"$lt": 0.8}}),
    ...     then_branch=expert_agents,
    ...     else_branch=fast_agents
    ... )
    >>> result = await cond_strategy.execute([], context)

"""

import logging

# Advanced Patterns 11-13 (extracted to _strategies/advanced_strategies.py)
from ._strategies.advanced_strategies import (
    DelegationChainStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
)
from ._strategies.base import ExecutionStrategy
from ._strategies.conditional_strategies import (
    ConditionalStrategy,
    MultiConditionalStrategy,
    NestedSequentialStrategy,
    NestedStrategy,
    StepDefinition,  # noqa: F401 - re-exported
)
from ._strategies.conditions import (
    Branch,  # noqa: F401 - re-exported
    Condition,  # noqa: F401 - re-exported
    ConditionEvaluator,  # noqa: F401 - re-exported
    ConditionType,  # noqa: F401 - re-exported
)
from ._strategies.core_strategies import (
    AdaptiveStrategy,
    DebateStrategy,
    ParallelStrategy,
    RefinementStrategy,
    SequentialStrategy,
    TeachingStrategy,
)
from ._strategies.data_classes import (  # noqa: F401 - re-exported
    AgentResult,
    StrategyResult,
)

# Import from submodule for modular organization
from ._strategies.nesting import (
    WORKFLOW_REGISTRY,  # noqa: F401 - re-exported
    InlineWorkflow,  # noqa: F401 - re-exported
    NestingContext,  # noqa: F401 - re-exported
    WorkflowDefinition,  # noqa: F401 - re-exported
    WorkflowReference,  # noqa: F401 - re-exported
    get_workflow,  # noqa: F401 - re-exported
    register_workflow,  # noqa: F401 - re-exported
)
from .agent_templates import AgentTemplate  # noqa: F401 - used by advanced strategies

logger = logging.getLogger(__name__)


# Strategy registry for lookup by name
# Note: Core and conditional strategies are also in _strategies._STRATEGY_REGISTRY
STRATEGY_REGISTRY: dict[str, type[ExecutionStrategy]] = {
    # Original 7 patterns
    "sequential": SequentialStrategy,
    "parallel": ParallelStrategy,
    "debate": DebateStrategy,
    "teaching": TeachingStrategy,
    "refinement": RefinementStrategy,
    "adaptive": AdaptiveStrategy,
    "conditional": ConditionalStrategy,
    # Additional patterns
    "multi_conditional": MultiConditionalStrategy,
    "nested": NestedStrategy,
    "nested_sequential": NestedSequentialStrategy,
    # New Anthropic-inspired patterns (8-10)
    "tool_enhanced": ToolEnhancedStrategy,
    "prompt_cached_sequential": PromptCachedSequentialStrategy,
    "delegation_chain": DelegationChainStrategy,
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
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {strategy_name}. Available: {list(STRATEGY_REGISTRY.keys())}",
        )

    strategy_class = STRATEGY_REGISTRY[strategy_name]
    return strategy_class()
