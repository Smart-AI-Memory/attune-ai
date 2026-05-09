"""Meta-orchestrator for intelligent agent composition.

This module implements the core orchestration logic that analyzes tasks,
selects appropriate agents, and chooses composition patterns.

Security:
    - All inputs validated before processing
    - No eval() or exec() usage
    - Agent selection based on whitelisted templates

Example:
    >>> orchestrator = MetaOrchestrator()
    >>> plan = orchestrator.analyze_and_compose(
    ...     task="Boost test coverage to 90%",
    ...     context={"current_coverage": 75}
    ... )
    >>> print(plan.strategy)
    sequential
    >>> print([a.role for a in plan.agents])
    ['Test Coverage Expert', 'Test Generation Specialist', 'Quality Assurance Validator']

"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .agent_templates import AgentTemplate, get_template, get_templates_by_capability  # noqa: F401

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity classification."""

    SIMPLE = "simple"  # Single agent, straightforward
    MODERATE = "moderate"  # 2-3 agents, some coordination
    COMPLEX = "complex"  # 4+ agents, multi-phase execution


class TaskDomain(Enum):
    """Task domain classification."""

    TESTING = "testing"
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    REFACTORING = "refactoring"
    GENERAL = "general"


class CompositionPattern(Enum):
    """Available composition patterns (grammar rules)."""

    # Original 7 patterns
    SEQUENTIAL = "sequential"  # A → B → C
    PARALLEL = "parallel"  # A || B || C
    DEBATE = "debate"  # A ⇄ B ⇄ C → Synthesis
    TEACHING = "teaching"  # Junior → Expert validation
    REFINEMENT = "refinement"  # Draft → Review → Polish
    ADAPTIVE = "adaptive"  # Classifier → Specialist
    CONDITIONAL = "conditional"  # If-then-else routing

    # Anthropic-inspired patterns (Patterns 8-10)
    TOOL_ENHANCED = "tool_enhanced"  # Single agent with tools
    PROMPT_CACHED_SEQUENTIAL = "prompt_cached_sequential"  # Shared cached context
    DELEGATION_CHAIN = "delegation_chain"  # Hierarchical delegation (≤3 levels)


@dataclass
class TaskRequirements:
    """Extracted requirements from task analysis.

    Attributes:
        complexity: Task complexity level
        domain: Primary task domain
        capabilities_needed: List of capabilities required
        parallelizable: Whether task can be parallelized
        quality_gates: Quality thresholds to enforce
        context: Additional context for customization

    """

    complexity: TaskComplexity
    domain: TaskDomain
    capabilities_needed: list[str]
    parallelizable: bool = False
    quality_gates: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Plan for agent execution.

    Attributes:
        agents: List of agents to execute
        strategy: Composition pattern to use
        quality_gates: Quality thresholds to enforce
        estimated_cost: Estimated execution cost
        estimated_duration: Estimated time in seconds

    """

    agents: list[AgentTemplate]
    strategy: CompositionPattern
    quality_gates: dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 0.0
    estimated_duration: int = 0


from .meta_orch_analysis import TaskAnalysisMixin  # noqa: E402
from .meta_orch_estimation import EstimationMixin  # noqa: E402
from .meta_orch_interactive import InteractiveModeMixin  # noqa: E402


class MetaOrchestrator(TaskAnalysisMixin, InteractiveModeMixin, EstimationMixin):
    """Intelligent task analyzer and agent composition engine.

    The meta-orchestrator analyzes tasks to determine requirements,
    selects appropriate agents, and chooses optimal composition patterns.

    Example:
        >>> orchestrator = MetaOrchestrator()
        >>> plan = orchestrator.analyze_and_compose(
        ...     task="Prepare for v3.12.0 release",
        ...     context={"version": "3.12.0"}
        ... )

    """

    def __init__(self):
        """Initialize meta-orchestrator."""
        logger.info("MetaOrchestrator initialized")

    def analyze_task(self, task: str, context: dict[str, Any] | None = None) -> TaskRequirements:
        """Analyze task to extract requirements (public wrapper for testing).

        Args:
            task: Task description (e.g., "Boost test coverage to 90%")
            context: Optional context dictionary

        Returns:
            TaskRequirements with extracted information

        Raises:
            ValueError: If task is invalid

        Example:
            >>> orchestrator = MetaOrchestrator()
            >>> requirements = orchestrator.analyze_task(
            ...     task="Improve test coverage",
            ...     context={"current_coverage": 75}
            ... )
            >>> print(requirements.domain)
            TaskDomain.TESTING

        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")

        context = context or {}
        return self._analyze_task(task, context)

    def create_execution_plan(
        self,
        requirements: TaskRequirements,
        agents: list[AgentTemplate],
        strategy: CompositionPattern,
    ) -> ExecutionPlan:
        """Create execution plan from components (extracted for testing).

        Args:
            requirements: Task requirements with quality gates
            agents: Selected agents for execution
            strategy: Composition pattern to use

        Returns:
            ExecutionPlan with all components configured

        Example:
            >>> orchestrator = MetaOrchestrator()
            >>> requirements = TaskRequirements(
            ...     complexity=TaskComplexity.MODERATE,
            ...     domain=TaskDomain.TESTING,
            ...     capabilities_needed=["analyze_gaps"],
            ...     quality_gates={"min_coverage": 80}
            ... )
            >>> agents = [get_template("test_coverage_analyzer")]
            >>> strategy = CompositionPattern.SEQUENTIAL
            >>> plan = orchestrator.create_execution_plan(requirements, agents, strategy)
            >>> print(plan.strategy)
            CompositionPattern.SEQUENTIAL

        """
        return ExecutionPlan(
            agents=agents,
            strategy=strategy,
            quality_gates=requirements.quality_gates,
            estimated_cost=self._estimate_cost(agents),
            estimated_duration=self._estimate_duration(agents, strategy),
        )

    def analyze_and_compose(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        interactive: bool = False,
    ) -> ExecutionPlan:
        """Analyze task and create execution plan.

        This is the main entry point for the meta-orchestrator.

        Args:
            task: Task description (e.g., "Boost test coverage to 90%")
            context: Optional context dictionary
            interactive: If True, prompts user for low-confidence cases (default: False)

        Returns:
            ExecutionPlan with agents and strategy

        Raises:
            ValueError: If task is invalid

        Example:
            >>> orchestrator = MetaOrchestrator()
            >>> plan = orchestrator.analyze_and_compose(
            ...     task="Improve test coverage",
            ...     context={"current_coverage": 75}
            ... )

        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")

        context = context or {}

        # Use interactive mode if requested
        if interactive:
            return self.analyze_and_compose_interactive(task, context)

        logger.info(f"Analyzing task: {task}")

        # Step 1: Analyze task requirements
        requirements = self._analyze_task(task, context)
        logger.info(
            f"Task analysis: complexity={requirements.complexity.value}, "
            f"domain={requirements.domain.value}, "
            f"capabilities={requirements.capabilities_needed}",
        )

        # Step 2: Select appropriate agents
        agents = self._select_agents(requirements)
        logger.info(f"Selected {len(agents)} agents: {[a.id for a in agents]}")

        # Step 3: Choose composition pattern
        strategy = self._choose_composition_pattern(requirements, agents)
        logger.info(f"Selected strategy: {strategy.value}")

        # Step 4: Create execution plan (using extracted public method)
        plan = self.create_execution_plan(requirements, agents, strategy)

        return plan

    def compose_team(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        state_store: Any | None = None,
        redis_client: Any | None = None,
    ) -> Any:
        """Analyze a task, compose agents, and return a runnable DynamicTeam.

        Combines ``analyze_and_compose()`` with ``DynamicTeamBuilder.build_from_plan()``
        to produce a team that can be executed immediately.

        Args:
            task: Natural language task description.
            context: Optional context dict.
            state_store: Optional ``AgentStateStore`` for persistent state.
            redis_client: Optional Redis client for coordination.

        Returns:
            A ``DynamicTeam`` instance ready to call ``execute()``.

        """
        from attune.orchestration.team_builder import DynamicTeamBuilder

        plan = self.analyze_and_compose(task, context)

        # Convert ExecutionPlan into the dict format DynamicTeamBuilder expects.
        # ExecutionPlan has no `phases` field — use [] so DynamicTeamBuilder.get()
        # picks up the same default.
        plan_dict: dict[str, Any] = {
            "name": f"team-{plan.strategy.value}",
            "strategy": plan.strategy.value,
            "agents": [{"template_id": t.id, "role": t.role} for t in plan.agents],
            "quality_gates": plan.quality_gates,
            "phases": [],
        }

        builder = DynamicTeamBuilder(
            state_store=state_store,
            redis_client=redis_client,
        )
        return builder.build_from_plan(plan_dict)
