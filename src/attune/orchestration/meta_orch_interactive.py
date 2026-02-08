"""Meta-orchestrator Interactive Mode.

Interactive analysis, confidence scoring, user prompts, team building,
and pattern selection wizards. Extracted from meta_orchestrator.py
for maintainability.

Contains:
- InteractiveModeMixin: Interactive analysis, confidence scoring,
  user prompts, team builder, pattern chooser

Expected attributes on the host class:
    _analyze_task: method (from TaskAnalysisMixin)
    _select_agents: method (from TaskAnalysisMixin)
    _choose_composition_pattern: method (from TaskAnalysisMixin)
    create_execution_plan: method (from MetaOrchestrator)

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from .agent_templates import AgentTemplate
from .meta_orchestrator import (
    CompositionPattern,
    ExecutionPlan,
    TaskComplexity,
    TaskDomain,
    TaskRequirements,
)

logger = logging.getLogger(__name__)


class InteractiveModeMixin:
    """Mixin providing interactive mode for meta-orchestrator."""

    def analyze_and_compose_interactive(
        self, task: str, context: dict[str, Any] | None = None
    ) -> ExecutionPlan:
        """Analyze task with user confirmation for ambiguous cases.

        This method uses confidence scoring to determine when to ask the user
        for input. High-confidence selections proceed automatically, while
        low-confidence cases prompt the user to choose.

        Args:
            task: Task description
            context: Optional context dictionary

        Returns:
            ExecutionPlan with agents and strategy

        Raises:
            ValueError: If task is invalid
            ImportError: If AskUserQuestion tool is not available

        Example:
            >>> orchestrator = MetaOrchestrator()
            >>> plan = orchestrator.analyze_and_compose_interactive(
            ...     task="Complex architectural redesign",
            ...     context={}
            ... )
            # User may be prompted to choose approach if confidence is low
        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")

        context = context or {}
        logger.info(f"Analyzing task interactively: {task}")

        # Step 1: Analyze task requirements
        requirements = self._analyze_task(task, context)
        logger.info(
            f"Task analysis: complexity={requirements.complexity.value}, "
            f"domain={requirements.domain.value}"
        )

        # Step 2: Select agents
        agents = self._select_agents(requirements)
        logger.info(f"Selected {len(agents)} agents: {[a.id for a in agents]}")

        # Step 3: Choose pattern
        recommended_pattern = self._choose_composition_pattern(requirements, agents)
        logger.info(f"Recommended strategy: {recommended_pattern.value}")

        # Step 4: Calculate confidence in recommendation
        confidence = self._calculate_confidence(requirements, agents, recommended_pattern)
        logger.info(f"Confidence score: {confidence:.2f}")

        # Step 5: Branch based on confidence
        if confidence >= 0.8:
            # High confidence → automatic execution
            logger.info("High confidence - proceeding automatically")
            return self.create_execution_plan(requirements, agents, recommended_pattern)

        else:
            # Low confidence → ask user
            logger.info("Low confidence - prompting user for choice")
            return self._prompt_user_for_approach(
                requirements, agents, recommended_pattern, confidence
            )

    def _calculate_confidence(
        self,
        requirements: TaskRequirements,
        agents: list[AgentTemplate],
        pattern: CompositionPattern,
    ) -> float:
        """Calculate confidence in automatic pattern selection.

        Confidence scoring considers:
        - Domain clarity (GENERAL domain reduces confidence)
        - Agent count (many agents = complex coordination)
        - Task complexity (complex tasks have multiple valid approaches)
        - Pattern specificity (Anthropic patterns have clear heuristics)

        Args:
            requirements: Task requirements
            agents: Selected agents
            pattern: Recommended composition pattern

        Returns:
            Confidence score between 0.0 and 1.0

        Example:
            >>> confidence = orchestrator._calculate_confidence(
            ...     requirements=TaskRequirements(
            ...         complexity=TaskComplexity.SIMPLE,
            ...         domain=TaskDomain.TESTING,
            ...         capabilities_needed=["analyze_gaps"]
            ...     ),
            ...     agents=[test_agent],
            ...     pattern=CompositionPattern.SEQUENTIAL
            ... )
            >>> confidence >= 0.8  # High confidence for simple, clear task
            True
        """
        confidence = 1.0

        # Reduce confidence for ambiguous cases
        if requirements.domain == TaskDomain.GENERAL:
            confidence *= 0.7  # Generic tasks are less clear

        if len(agents) > 5:
            confidence *= 0.8  # Many agents → complex coordination

        if requirements.complexity == TaskComplexity.COMPLEX:
            confidence *= 0.85  # Complex → multiple valid approaches

        # Increase confidence for clear patterns
        if pattern in [
            CompositionPattern.TOOL_ENHANCED,
            CompositionPattern.DELEGATION_CHAIN,
            CompositionPattern.PROMPT_CACHED_SEQUENTIAL,
        ]:
            confidence *= 1.1  # New Anthropic patterns have clear heuristics

        # Specific domain patterns also get confidence boost
        if pattern in [
            CompositionPattern.TEACHING,
            CompositionPattern.REFINEMENT,
        ] and requirements.domain in [TaskDomain.DOCUMENTATION, TaskDomain.REFACTORING]:
            confidence *= 1.05  # Domain-specific pattern match

        return min(confidence, 1.0)

    def _prompt_user_for_approach(
        self,
        requirements: TaskRequirements,
        agents: list[AgentTemplate],
        recommended_pattern: CompositionPattern,
        confidence: float,
    ) -> ExecutionPlan:
        """Prompt user to choose approach when confidence is low.

        Presents three options:
        1. Use recommended pattern (with confidence score)
        2. Customize team composition
        3. Show all patterns and choose

        Args:
            requirements: Task requirements
            agents: Selected agents
            recommended_pattern: Recommended pattern
            confidence: Confidence score (0.0-1.0)

        Returns:
            ExecutionPlan based on user choice

        Raises:
            ImportError: If AskUserQuestion tool not available
        """
        try:
            # Import here to avoid circular dependency and allow graceful degradation
            from attune.tools import AskUserQuestion
        except ImportError as e:
            logger.warning(f"AskUserQuestion not available: {e}")
            logger.info("Falling back to automatic selection")
            return self.create_execution_plan(requirements, agents, recommended_pattern)

        # Format agent list for display
        agent_summary = ", ".join([a.role for a in agents])

        # Ask user for approach
        try:
            response = AskUserQuestion(
                questions=[
                    {
                        "header": "Approach",
                        "question": "How would you like to create the agent team?",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": f"Use recommended: {recommended_pattern.value} (Recommended)",
                                "description": f"Auto-selected based on task analysis. "
                                f"{len(agents)} agents: {agent_summary}. "
                                f"Confidence: {confidence:.0%}",
                            },
                            {
                                "label": "Customize team composition",
                                "description": "Choose specific agents and pattern manually",
                            },
                            {
                                "label": "Show all 10 patterns",
                                "description": "Learn about patterns and select one",
                            },
                        ],
                    }
                ]
            )
        except (NotImplementedError, RuntimeError) as e:
            logger.warning(f"AskUserQuestion unavailable: {e}")
            logger.info("Falling back to automatic selection")
            return self.create_execution_plan(requirements, agents, recommended_pattern)

        # Handle user response
        user_choice = response.get("Approach", "")

        if "Use recommended" in user_choice:
            logger.info("User accepted recommended approach")
            return self.create_execution_plan(requirements, agents, recommended_pattern)

        elif "Customize" in user_choice:
            logger.info("User chose to customize team")
            return self._interactive_team_builder(requirements, agents, recommended_pattern)

        else:  # Show patterns
            logger.info("User chose to explore patterns")
            return self._pattern_chooser_wizard(requirements, agents)

    def _interactive_team_builder(
        self,
        requirements: TaskRequirements,
        suggested_agents: list[AgentTemplate],
        suggested_pattern: CompositionPattern,
    ) -> ExecutionPlan:
        """Interactive team builder for manual customization.

        Allows user to:
        1. Review suggested agents and modify selection
        2. Choose composition pattern
        3. Configure quality gates

        Args:
            requirements: Task requirements
            suggested_agents: Auto-selected agents
            suggested_pattern: Auto-selected pattern

        Returns:
            ExecutionPlan with user-customized configuration
        """
        try:
            from attune.tools import AskUserQuestion
        except ImportError:
            logger.warning("AskUserQuestion not available, using defaults")
            return self.create_execution_plan(requirements, suggested_agents, suggested_pattern)

        # Step 1: Agent selection
        try:
            agent_response = AskUserQuestion(
                questions=[
                    {
                        "header": "Agents",
                        "question": "Which agents should be included in the team?",
                        "multiSelect": True,
                        "options": [
                            {
                                "label": agent.role,
                                "description": f"{agent.id} - {', '.join(agent.capabilities[:3])}",
                            }
                            for agent in suggested_agents
                        ],
                    }
                ]
            )
        except (NotImplementedError, RuntimeError) as e:
            logger.warning(f"AskUserQuestion unavailable: {e}")
            return self.create_execution_plan(requirements, suggested_agents, suggested_pattern)

        # Filter agents based on user selection
        selected_agent_roles = agent_response.get("Agents", [])
        if not isinstance(selected_agent_roles, list):
            selected_agent_roles = [selected_agent_roles]

        selected_agents = [a for a in suggested_agents if a.role in selected_agent_roles]
        if not selected_agents:
            # User deselected all - use defaults
            selected_agents = suggested_agents

        # Step 2: Pattern selection
        try:
            pattern_response = AskUserQuestion(
                questions=[
                    {
                        "header": "Pattern",
                        "question": "Which composition pattern should be used?",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": f"{suggested_pattern.value} (Recommended)",
                                "description": self._get_pattern_description(suggested_pattern),
                            },
                            {
                                "label": "sequential",
                                "description": "Execute agents one after another (A → B → C)",
                            },
                            {
                                "label": "parallel",
                                "description": "Execute agents simultaneously (A || B || C)",
                            },
                            {
                                "label": "tool_enhanced",
                                "description": "Single agent with comprehensive tool access",
                            },
                        ],
                    }
                ]
            )
        except (NotImplementedError, RuntimeError) as e:
            logger.warning(f"AskUserQuestion unavailable: {e}")
            return self.create_execution_plan(requirements, selected_agents, suggested_pattern)

        # Parse pattern choice
        pattern_choice = pattern_response.get("Pattern", suggested_pattern.value)
        if "(Recommended)" in pattern_choice:
            selected_pattern = suggested_pattern
        else:
            # Extract pattern name
            pattern_name = pattern_choice.split()[0]
            try:
                selected_pattern = CompositionPattern(pattern_name)
            except ValueError:
                logger.warning(f"Invalid pattern: {pattern_name}, using suggested")
                selected_pattern = suggested_pattern

        # Create execution plan with user selections
        return self.create_execution_plan(requirements, selected_agents, selected_pattern)

    def _pattern_chooser_wizard(
        self,
        requirements: TaskRequirements,
        suggested_agents: list[AgentTemplate],
    ) -> ExecutionPlan:
        """Interactive pattern chooser with educational previews.

        Shows all 10 composition patterns with:
        - Description and when to use
        - Visual preview of agent flow
        - Estimated cost and duration
        - Examples of similar tasks

        Args:
            requirements: Task requirements
            suggested_agents: Auto-selected agents

        Returns:
            ExecutionPlan with user-selected pattern
        """
        try:
            from attune.tools import AskUserQuestion
        except ImportError:
            logger.warning("AskUserQuestion not available, using defaults")
            suggested_pattern = self._choose_composition_pattern(requirements, suggested_agents)
            return self.create_execution_plan(requirements, suggested_agents, suggested_pattern)

        # Present all patterns with descriptions
        try:
            pattern_response = AskUserQuestion(
                questions=[
                    {
                        "header": "Pattern",
                        "question": "Choose a composition pattern (with preview):",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": "sequential",
                                "description": "A → B → C | Step-by-step pipeline | "
                                "Example: Parse → Analyze → Report",
                            },
                            {
                                "label": "parallel",
                                "description": "A || B || C | Independent tasks | "
                                "Example: Security + Quality + Performance audits",
                            },
                            {
                                "label": "debate",
                                "description": "A ⇄ B ⇄ C → Synthesis | Multiple perspectives | "
                                "Example: 3 reviewers discuss approach",
                            },
                            {
                                "label": "teaching",
                                "description": "Junior → Expert validation | Draft + review | "
                                "Example: Cheap model drafts, expert validates",
                            },
                            {
                                "label": "refinement",
                                "description": "Draft → Review → Polish | Iterative improvement | "
                                "Example: Code → Review → Refine",
                            },
                            {
                                "label": "adaptive",
                                "description": "Classifier → Specialist | Dynamic routing | "
                                "Example: Analyze task type → Route to expert",
                            },
                            {
                                "label": "tool_enhanced (NEW)",
                                "description": "Single agent + tools | Most efficient | "
                                "Example: File reader with analysis tools",
                            },
                            {
                                "label": "prompt_cached_sequential (NEW)",
                                "description": "Shared large context | Cost-optimized | "
                                "Example: 3 agents using same codebase docs",
                            },
                            {
                                "label": "delegation_chain (NEW)",
                                "description": "Coordinator → Specialists | Hierarchical | "
                                "Example: Task planner delegates to architects",
                            },
                        ],
                    }
                ]
            )
        except (NotImplementedError, RuntimeError) as e:
            logger.warning(f"AskUserQuestion unavailable: {e}")
            suggested_pattern = self._choose_composition_pattern(requirements, suggested_agents)
            return self.create_execution_plan(requirements, suggested_agents, suggested_pattern)

        # Parse pattern choice
        pattern_choice = pattern_response.get("Pattern", "sequential")
        pattern_name = pattern_choice.split()[0]  # Extract name before any annotations

        try:
            selected_pattern = CompositionPattern(pattern_name)
        except ValueError:
            logger.warning(f"Invalid pattern: {pattern_name}, using sequential")
            selected_pattern = CompositionPattern.SEQUENTIAL

        logger.info(f"User selected pattern: {selected_pattern.value}")

        # Create execution plan with user-selected pattern
        return self.create_execution_plan(requirements, suggested_agents, selected_pattern)

    def _get_pattern_description(self, pattern: CompositionPattern) -> str:
        """Get human-readable description of a pattern.

        Args:
            pattern: Composition pattern

        Returns:
            Description string
        """
        descriptions = {
            CompositionPattern.SEQUENTIAL: "Execute agents one after another (A → B → C)",
            CompositionPattern.PARALLEL: "Execute agents simultaneously (A || B || C)",
            CompositionPattern.DEBATE: "Multiple agents discuss and synthesize (A ⇄ B → Result)",
            CompositionPattern.TEACHING: "Junior agent with expert validation (Draft → Review)",
            CompositionPattern.REFINEMENT: "Iterative improvement (Draft → Review → Polish)",
            CompositionPattern.ADAPTIVE: "Dynamic routing based on classification",
            CompositionPattern.CONDITIONAL: "If-then-else branching logic",
            CompositionPattern.TOOL_ENHANCED: "Single agent with comprehensive tool access",
            CompositionPattern.PROMPT_CACHED_SEQUENTIAL: "Sequential with shared cached context",
            CompositionPattern.DELEGATION_CHAIN: "Hierarchical coordinator → specialists",
        }
        return descriptions.get(pattern, "Custom composition pattern")
