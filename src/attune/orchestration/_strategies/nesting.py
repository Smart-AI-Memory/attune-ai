"""Workflow nesting support for recursive composition.

This module enables "sentences within sentences" - workflows that invoke
other workflows. Supports both registered workflow IDs and inline definitions.

Key concepts:
- WorkflowReference: Points to a nested workflow (by ID or inline)
- InlineWorkflow: Defines a sub-workflow directly within parent
- NestingContext: Tracks depth and prevents infinite recursion
- WorkflowDefinition: A registered workflow that can be referenced by ID

Security:
    - Cycle detection prevents infinite loops
    - Max depth limit prevents stack overflow
    - No eval() or exec() usage

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agent_templates import AgentTemplate

logger = logging.getLogger(__name__)


# =============================================================================
# Nested Sentence Types (Phase 2 - Recursive Composition)
# =============================================================================


@dataclass
class WorkflowReference:
    """Reference to a workflow for nested composition.

    Enables "sentences within sentences" - workflows that invoke other workflows.
    Supports both registered workflow IDs and inline definitions.

    Attributes:
        workflow_id: ID of registered workflow (mutually exclusive with inline)
        inline: Inline workflow definition (mutually exclusive with workflow_id)
        context_mapping: Optional mapping of parent context fields to child
        result_key: Key to store nested workflow result in parent context

    Example (by ID):
        >>> ref = WorkflowReference(
        ...     workflow_id="security-audit-team",
        ...     result_key="security_result"
        ... )

    Example (inline):
        >>> ref = WorkflowReference(
        ...     inline=InlineWorkflow(
        ...         agents=[agent1, agent2],
        ...         strategy="parallel"
        ...     ),
        ...     result_key="analysis_result"
        ... )

    """

    workflow_id: str = ""
    inline: InlineWorkflow | None = None
    context_mapping: dict[str, str] = field(default_factory=dict)
    result_key: str = "nested_result"

    def __post_init__(self):
        """Validate that exactly one reference type is provided."""
        if bool(self.workflow_id) == bool(self.inline):
            raise ValueError("WorkflowReference must have exactly one of: workflow_id or inline")


@dataclass
class InlineWorkflow:
    """Inline workflow definition for nested composition.

    Allows defining a sub-workflow directly within a parent workflow,
    without requiring registration.

    Attributes:
        agents: Agents to execute
        strategy: Strategy name (from STRATEGY_REGISTRY)
        description: Human-readable description

    Example:
        >>> inline = InlineWorkflow(
        ...     agents=[analyzer, reviewer],
        ...     strategy="sequential",
        ...     description="Code review sub-workflow"
        ... )

    """

    agents: list[AgentTemplate]
    strategy: str = "sequential"
    description: str = ""


class NestingContext:
    """Tracks nesting depth and prevents infinite recursion.

    Attributes:
        current_depth: Current nesting level (0 = root)
        max_depth: Maximum allowed nesting depth
        workflow_stack: Stack of workflow IDs for cycle detection

    """

    CONTEXT_KEY = "_nesting"
    DEFAULT_MAX_DEPTH = 3

    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH):
        """Initialize nesting context.

        Args:
            max_depth: Maximum allowed nesting depth

        """
        self.current_depth = 0
        self.max_depth = max_depth
        self.workflow_stack: list[str] = []

    @classmethod
    def from_context(cls, context: dict[str, Any]) -> NestingContext:
        """Extract or create NestingContext from execution context.

        Args:
            context: Execution context dict

        Returns:
            NestingContext instance

        """
        if cls.CONTEXT_KEY in context:
            return context[cls.CONTEXT_KEY]
        return cls()

    def can_nest(self, workflow_id: str = "") -> bool:
        """Check if another nesting level is allowed.

        Args:
            workflow_id: ID of workflow to nest (for cycle detection)

        Returns:
            True if nesting is allowed

        """
        if self.current_depth >= self.max_depth:
            return False
        if workflow_id and workflow_id in self.workflow_stack:
            return False  # Cycle detected
        return True

    def enter(self, workflow_id: str = "") -> NestingContext:
        """Create a child context for nested execution.

        Args:
            workflow_id: ID of workflow being entered

        Returns:
            New NestingContext with incremented depth

        """
        child = NestingContext(self.max_depth)
        child.current_depth = self.current_depth + 1
        child.workflow_stack = self.workflow_stack.copy()
        if workflow_id:
            child.workflow_stack.append(workflow_id)
        return child

    def to_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """Add nesting context to execution context.

        Args:
            context: Execution context dict

        Returns:
            Updated context with nesting info

        """
        context = context.copy()
        context[self.CONTEXT_KEY] = self
        return context


# Registry for named workflows (populated at runtime)
WORKFLOW_REGISTRY: dict[str, WorkflowDefinition] = {}


@dataclass
class WorkflowDefinition:
    """A registered workflow definition.

    Workflows can be registered and referenced by ID in nested compositions.

    Attributes:
        id: Unique workflow identifier
        agents: Agents in the workflow
        strategy: Composition strategy name
        description: Human-readable description

    """

    id: str
    agents: list[AgentTemplate]
    strategy: str = "sequential"
    description: str = ""


def register_workflow(workflow: WorkflowDefinition) -> None:
    """Register a workflow for nested references.

    Args:
        workflow: Workflow definition to register

    """
    WORKFLOW_REGISTRY[workflow.id] = workflow
    logger.info(f"Registered workflow: {workflow.id}")


def get_workflow(workflow_id: str) -> WorkflowDefinition:
    """Get a registered workflow by ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        WorkflowDefinition

    Raises:
        ValueError: If workflow is not registered

    """
    if workflow_id not in WORKFLOW_REGISTRY:
        raise ValueError(
            f"Unknown workflow: {workflow_id}. Available: {list(WORKFLOW_REGISTRY.keys())}",
        )
    return WORKFLOW_REGISTRY[workflow_id]
