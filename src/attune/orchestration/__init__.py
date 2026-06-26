"""Orchestration primitives: agent templates and execution strategies.

This package provides the live orchestration building blocks used by
workflows: reusable agent-template *data* (consumed as prompt/routing
metadata) and the execution-strategy implementations used by the
``health-check`` orchestrated workflow.

Example:
    >>> from attune.orchestration import AgentTemplate, get_template
    >>> template = get_template("test_coverage_analyzer")
    >>> print(template.role)
    Test Coverage Expert

    >>> from attune.orchestration import get_strategy
    >>> strategy = get_strategy("tool_enhanced")
    >>> print(strategy.__class__.__name__)
    ToolEnhancedStrategy

"""

from attune.orchestration.agent_templates import (
    AgentCapability,
    AgentTemplate,
    ResourceRequirements,
    get_all_templates,
    get_registry,
    get_template,
    get_templates_by_capability,
    get_templates_by_tier,
    register_custom_template,
    unregister_template,
)
from attune.orchestration.execution_strategies import (
    DelegationChainStrategy,
    ExecutionStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
    get_strategy,
)

__all__ = [
    # Agent Templates
    "AgentTemplate",
    "AgentCapability",
    "ResourceRequirements",
    "get_template",
    "get_all_templates",
    "get_registry",
    "get_templates_by_capability",
    "get_templates_by_tier",
    "register_custom_template",
    "unregister_template",
    # Execution Strategies
    "ExecutionStrategy",
    "get_strategy",
    # Anthropic-Inspired Patterns (Patterns 8-10)
    "ToolEnhancedStrategy",
    "PromptCachedSequentialStrategy",
    "DelegationChainStrategy",
]
