"""Conditional and nested execution strategies.

This module contains strategies that implement conditional branching and
nested workflow composition:

1. ConditionalStrategy - if/then/else branching based on gates
2. MultiConditionalStrategy - switch/case pattern
3. NestedStrategy - recursive workflow execution
4. NestedSequentialStrategy - sequential steps with nested workflow support

Security:
    - Condition predicates validated (no code execution)
    - Cycle detection prevents infinite recursion
    - Max depth limits enforced
    - No eval() or exec() usage

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import ExecutionStrategy
from .conditions import Condition, ConditionEvaluator
from .data_classes import AgentResult, StrategyResult
from .nesting import (
    NestingContext,
    WorkflowReference,
    get_workflow,
)

if TYPE_CHECKING:
    from ..agent_templates import AgentTemplate
    from .conditions import Branch

logger = logging.getLogger(__name__)


class ConditionalStrategy(ExecutionStrategy):
    """Conditional branching (if X then A else B).

    The 7th grammar rule enabling dynamic workflow decisions based on gates.

    Use when:
        - Quality gates determine next steps
        - Error handling requires different paths
        - Agent consensus affects workflow
    """

    def __init__(
        self,
        condition: Condition,
        then_branch: Branch,
        else_branch: Branch | None = None,
    ):
        """Initialize conditional strategy."""
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.evaluator = ConditionEvaluator()

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute conditional branching."""
        # Import here to avoid circular import
        from . import get_strategy

        logger.info(f"Conditional: Evaluating '{self.condition.description or 'condition'}'")

        condition_met = self.evaluator.evaluate(self.condition, context)
        logger.info(f"Conditional: Condition evaluated to {condition_met}")

        if condition_met:
            selected_branch = self.then_branch
            branch_label = "then"
        else:
            if self.else_branch is None:
                return StrategyResult(
                    success=True,
                    outputs=[],
                    aggregated_output={"branch_taken": None},
                    total_duration=0.0,
                )
            selected_branch = self.else_branch
            branch_label = "else"

        logger.info(f"Conditional: Taking '{branch_label}' branch")

        branch_strategy = get_strategy(selected_branch.strategy)
        branch_context = context.copy()
        branch_context["_conditional"] = {"condition_met": condition_met, "branch": branch_label}

        result = await branch_strategy.execute(selected_branch.agents, branch_context)
        result.aggregated_output["_conditional"] = {
            "condition_met": condition_met,
            "branch_taken": branch_label,
        }
        return result


class MultiConditionalStrategy(ExecutionStrategy):
    """Multiple conditional branches (switch/case pattern)."""

    def __init__(
        self,
        conditions: list[tuple[Condition, Branch]],
        default_branch: Branch | None = None,
    ):
        """Initialize multi-conditional strategy."""
        self.conditions = conditions
        self.default_branch = default_branch
        self.evaluator = ConditionEvaluator()

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute multi-conditional branching."""
        # Import here to avoid circular import
        from . import get_strategy

        for i, (condition, branch) in enumerate(self.conditions):
            if self.evaluator.evaluate(condition, context):
                logger.info(f"MultiConditional: Condition {i + 1} matched")
                branch_strategy = get_strategy(branch.strategy)
                result = await branch_strategy.execute(branch.agents, context)
                result.aggregated_output["_matched_index"] = i
                return result

        if self.default_branch:
            branch_strategy = get_strategy(self.default_branch.strategy)
            return await branch_strategy.execute(self.default_branch.agents, context)

        return StrategyResult(
            success=True,
            outputs=[],
            aggregated_output={"reason": "No conditions matched"},
            total_duration=0.0,
        )


class NestedStrategy(ExecutionStrategy):
    """Nested workflow execution (sentences within sentences).

    Enables recursive composition where workflows invoke other workflows.
    Implements the "subordinate clause" pattern in the grammar metaphor.

    Features:
        - Reference workflows by ID or define inline
        - Configurable max depth (default: 3)
        - Cycle detection prevents infinite recursion
        - Full context inheritance from parent to child

    Use when:
        - Complex multi-stage pipelines need modular sub-workflows
        - Reusable workflow components should be shared
        - Hierarchical team structures (teams containing sub-teams)

    Example:
        >>> # Parent workflow with nested sub-workflow
        >>> strategy = NestedStrategy(
        ...     workflow_ref=WorkflowReference(workflow_id="security-audit"),
        ...     max_depth=3
        ... )
        >>> result = await strategy.execute([], context)

    Example (inline):
        >>> strategy = NestedStrategy(
        ...     workflow_ref=WorkflowReference(
        ...         inline=InlineWorkflow(
        ...             agents=[analyzer, reviewer],
        ...             strategy="parallel"
        ...         )
        ...     )
        ... )

    """

    def __init__(
        self,
        workflow_ref: WorkflowReference,
        max_depth: int = NestingContext.DEFAULT_MAX_DEPTH,
    ):
        """Initialize nested strategy.

        Args:
            workflow_ref: Reference to workflow (by ID or inline)
            max_depth: Maximum nesting depth allowed

        """
        self.workflow_ref = workflow_ref
        self.max_depth = max_depth

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute nested workflow.

        Args:
            agents: Ignored (workflow_ref defines agents)
            context: Parent execution context (inherited by child)

        Returns:
            StrategyResult from nested workflow execution

        Raises:
            RecursionError: If max depth exceeded or cycle detected

        """
        # Import here to avoid circular import
        from . import get_strategy

        # Get or create nesting context
        nesting = NestingContext.from_context(context)

        # Resolve workflow
        if self.workflow_ref.workflow_id:
            workflow_id = self.workflow_ref.workflow_id
            workflow = get_workflow(workflow_id)
            workflow_agents = workflow.agents
            strategy_name = workflow.strategy
        else:
            workflow_id = f"inline_{id(self.workflow_ref.inline)}"
            workflow_agents = self.workflow_ref.inline.agents
            strategy_name = self.workflow_ref.inline.strategy

        # Check nesting limits
        if not nesting.can_nest(workflow_id):
            if nesting.current_depth >= nesting.max_depth:
                error_msg = (
                    f"Maximum nesting depth ({nesting.max_depth}) exceeded. "
                    f"Current stack: {' → '.join(nesting.workflow_stack)}"
                )
            else:
                error_msg = (
                    f"Cycle detected: workflow '{workflow_id}' already in stack. "
                    f"Stack: {' → '.join(nesting.workflow_stack)}"
                )
            logger.error(error_msg)
            raise RecursionError(error_msg)

        logger.info(f"Nested: Entering '{workflow_id}' at depth {nesting.current_depth + 1}")

        # Create child context with updated nesting
        child_nesting = nesting.enter(workflow_id)
        child_context = child_nesting.to_context(context.copy())

        # Execute nested workflow
        strategy = get_strategy(strategy_name)
        result = await strategy.execute(workflow_agents, child_context)

        # Augment result with nesting metadata
        result.aggregated_output["_nested"] = {
            "workflow_id": workflow_id,
            "depth": child_nesting.current_depth,
            "parent_stack": nesting.workflow_stack,
        }

        # Store result under specified key if provided
        if self.workflow_ref.result_key:
            result.aggregated_output[self.workflow_ref.result_key] = result.aggregated_output.copy()

        logger.info(f"Nested: Exiting '{workflow_id}'")

        return result


@dataclass
class StepDefinition:
    """Definition of a step in NestedSequentialStrategy.

    Either agent OR workflow_ref must be provided (mutually exclusive).

    Attributes:
        agent: Agent to execute directly
        workflow_ref: Nested workflow to execute

    """

    agent: AgentTemplate | None = None
    workflow_ref: WorkflowReference | None = None

    def __post_init__(self):
        """Validate that exactly one step type is provided."""
        if bool(self.agent) == bool(self.workflow_ref):
            raise ValueError("StepDefinition must have exactly one of: agent or workflow_ref")


class NestedSequentialStrategy(ExecutionStrategy):
    """Sequential execution with nested workflow support.

    Like SequentialStrategy but steps can be either agents OR workflow references.
    Enables mixing direct agent execution with nested sub-workflows.

    Example:
        >>> strategy = NestedSequentialStrategy(
        ...     steps=[
        ...         StepDefinition(agent=analyzer),
        ...         StepDefinition(workflow_ref=WorkflowReference(workflow_id="review-team")),
        ...         StepDefinition(agent=reporter),
        ...     ]
        ... )

    """

    def __init__(
        self,
        steps: list[StepDefinition],
        max_depth: int = NestingContext.DEFAULT_MAX_DEPTH,
    ):
        """Initialize nested sequential strategy.

        Args:
            steps: List of step definitions (agents or workflow refs)
            max_depth: Maximum nesting depth

        """
        self.steps = steps
        self.max_depth = max_depth

    async def execute(self, agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult:
        """Execute steps sequentially, handling both agents and nested workflows."""
        if not self.steps:
            raise ValueError("steps list cannot be empty")

        logger.info(f"NestedSequential: Executing {len(self.steps)} steps")

        results: list[AgentResult] = []
        current_context = context.copy()
        total_duration = 0.0

        for i, step in enumerate(self.steps):
            logger.info(f"NestedSequential: Step {i + 1}/{len(self.steps)}")

            if step.agent:
                # Direct agent execution
                result = await self._execute_agent(step.agent, current_context)
                results.append(result)
                total_duration += result.duration_seconds

                if result.success:
                    current_context[f"{step.agent.id}_output"] = result.output
            else:
                # Nested workflow execution
                nested_strategy = NestedStrategy(
                    workflow_ref=step.workflow_ref,
                    max_depth=self.max_depth,
                )
                nested_result = await nested_strategy.execute([], current_context)
                total_duration += nested_result.total_duration

                # Convert to AgentResult for consistency
                results.append(
                    AgentResult(
                        agent_id=f"nested_{step.workflow_ref.workflow_id or 'inline'}",
                        success=nested_result.success,
                        output=nested_result.aggregated_output,
                        confidence=nested_result.aggregated_output.get("avg_confidence", 0.0),
                        duration_seconds=nested_result.total_duration,
                    ),
                )

                if nested_result.success:
                    key = step.workflow_ref.result_key or f"step_{i}_output"
                    current_context[key] = nested_result.aggregated_output

        return StrategyResult(
            success=all(r.success for r in results),
            outputs=results,
            aggregated_output=self._aggregate_results(results),
            total_duration=total_duration,
            errors=[r.error for r in results if not r.success],
        )
