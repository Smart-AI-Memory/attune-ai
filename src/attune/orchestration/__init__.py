"""Meta-orchestration system for dynamic agent composition.

This package provides the infrastructure for dynamically composing
agent teams based on task requirements. It enables intelligent task
analysis, agent spawning, and execution strategy selection.

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
from attune.orchestration.dynamic_team import DynamicTeam, DynamicTeamResult
from attune.orchestration.execution_strategies import (
    DelegationChainStrategy,
    ExecutionStrategy,
    PromptCachedSequentialStrategy,
    ToolEnhancedStrategy,
    get_strategy,
)
from attune.orchestration.meta_orchestrator import (
    CompositionPattern,
    ExecutionPlan,
    MetaOrchestrator,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)
from attune.orchestration.team_builder import DynamicTeamBuilder
from attune.orchestration.team_driver import describe_team_for_task, run_team_for_task
from attune.orchestration.team_store import TeamSpecification, TeamStore
from attune.orchestration.workflow_agent_adapter import WorkflowAgentAdapter
from attune.orchestration.workflow_composer import WorkflowComposer

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
    # Dynamic Teams
    "DynamicTeam",
    "DynamicTeamBuilder",
    "DynamicTeamResult",
    "TeamSpecification",
    "TeamStore",
    # Claude-driven team access (interactive-orchestration-access Phase 2)
    "describe_team_for_task",
    "run_team_for_task",
    # Workflow Composition
    "WorkflowAgentAdapter",
    "WorkflowComposer",
    # Execution Strategies
    "ExecutionStrategy",
    "get_strategy",
    # Anthropic-Inspired Patterns (Patterns 8-10)
    "ToolEnhancedStrategy",
    "PromptCachedSequentialStrategy",
    "DelegationChainStrategy",
    # Meta-Orchestrator & Types
    "MetaOrchestrator",
    "ExecutionPlan",
    "CompositionPattern",
    "TaskComplexity",
    "TaskDomain",
    "TaskRequirements",
]
