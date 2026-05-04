---
type: reference
feature: orchestration
depth: reference
generated_at: 2026-05-04T02:36:14.097563+00:00
source_hash: 15dce809a43de06ae9f042882afecc50f3b625050abdca81b878a832140002f0
status: generated
---

# Orchestration reference

Coordinate multi-agent teams, compose execution strategies, and manage distributed memory networks for collaborative AI workflows.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `AgentTask` | Task assigned to an agent with status tracking | `src/attune/coordination/agent_coordinator.py` |
| `AgentCoordinator` | Redis-backed coordinator for multi-agent teams | `src/attune/coordination/agent_coordinator.py` |
| `ResolutionStrategy` | Strategy for resolving pattern conflicts | `src/attune/coordination/conflict_resolution.py` |
| `ResolutionResult` | Result of conflict resolution between patterns | `src/attune/coordination/conflict_resolution.py` |
| `TeamPriorities` | Team-configured priorities for conflict resolution | `src/attune/coordination/conflict_resolution.py` |
| `ConflictResolver` | Resolves conflicts between patterns from different agents | `src/attune/coordination/conflict_resolution.py` |
| `TeamSession` | Collaborative session for multiple agents working together | `src/attune/coordination/team_session.py` |
| `ToolEnhancedStrategy` | Single agent with comprehensive tool access | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `PromptCachedSequentialStrategy` | Sequential execution with shared cached context | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `DelegationChainStrategy` | Hierarchical delegation with max depth enforcement | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `ExecutionStrategy` | Base class for agent composition strategies | `src/attune/orchestration/_strategies/base.py` |
| `ConditionalStrategy` | Conditional branching (if X then A else B) | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `MultiConditionalStrategy` | Multiple conditional branches (switch/case pattern) | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `NestedStrategy` | Nested workflow execution (sentences within sentences) | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `StepDefinition` | Definition of a step in NestedSequentialStrategy | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `NestedSequentialStrategy` | Sequential execution with nested workflow support | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `ConditionType` | Type of condition for gate evaluation | `src/attune/orchestration/_strategies/conditions.py` |
| `Condition` | Conditional gate for branching in agent workflows | `src/attune/orchestration/_strategies/conditions.py` |
| `Branch` | Branch in conditional execution | `src/attune/orchestration/_strategies/conditions.py` |
| `ConditionEvaluator` | Evaluates conditions against execution context | `src/attune/orchestration/_strategies/conditions.py` |
| `SequentialStrategy` | Sequential composition (A → B → C) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `ParallelStrategy` | Parallel composition (A || B || C) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `DebateStrategy` | Debate/Consensus composition (A ⇄ B ⇄ C → Synthesis) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `TeachingStrategy` | Teaching/Validation (Junior → Expert Review) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `RefinementStrategy` | Progressive Refinement (Draft → Review → Polish) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `AdaptiveStrategy` | Adaptive Routing (Classifier → Specialist) | `src/attune/orchestration/_strategies/core_strategies.py` |
| `AgentResult` | Result from agent execution | `src/attune/orchestration/_strategies/data_classes.py` |
| `StrategyResult` | Aggregated result from strategy execution | `src/attune/orchestration/_strategies/data_classes.py` |
| `WorkflowReference` | Reference to a workflow for nested composition | `src/attune/orchestration/_strategies/nesting.py` |
| `InlineWorkflow` | Inline workflow definition for nested composition | `src/attune/orchestration/_strategies/nesting.py` |
| `NestingContext` | Tracks nesting depth and prevents infinite recursion | `src/attune/orchestration/_strategies/nesting.py` |
| `WorkflowDefinition` | Registered workflow definition | `src/attune/orchestration/_strategies/nesting.py` |
| `SDKExecutionMode` | Execution mode for agent runtime | `src/attune/orchestration/agent_models.py` |
| `SDKAgentResult` | Result from a single agent execution | `src/attune/orchestration/agent_models.py` |
| `QualityGate` | Named threshold that an agent result must satisfy | `src/attune/orchestration/agent_models.py` |
| `AgentLike` | Protocol for objects that can participate in DynamicTeam execution | `src/attune/orchestration/agent_models.py` |
| `StubAgent` | Lightweight agent stub for DynamicTeam composition | `src/attune/orchestration/agent_models.py` |
| `AgentCapability` | Capability that an agent can perform | `src/attune/orchestration/agent_templates/models.py` |
| `ResourceRequirements` | Resource requirements for agent execution | `src/attune/orchestration/agent_templates/models.py` |
| `AgentTemplate` | Reusable agent archetype | `src/attune/orchestration/agent_templates/models.py` |
| `AgentConfiguration` | Saved configuration for a successful agent team composition | `src/attune/orchestration/config_store.py` |
| `ConfigurationStore` | Persistent storage for successful agent team compositions | `src/attune/orchestration/config_store.py` |
| `DynamicTeamResult` | Aggregated result from a DynamicTeam execution | `src/attune/orchestration/dynamic_team.py` |
| `DynamicTeam` | Executes a dynamically-composed agent team | `src/attune/orchestration/dynamic_team.py` |
| `TaskAnalysisMixin` | Task analysis and agent selection for meta-orchestrator | `src/attune/orchestration/meta_orch_analysis.py` |
| `EstimationMixin` | Cost and duration estimation for meta-orchestrator | `src/attune/orchestration/meta_orch_estimation.py` |
| `InteractiveModeMixin` | Interactive mode for meta-orchestrator | `src/attune/orchestration/meta_orch_interactive.py` |
| `TaskComplexity` | Task complexity classification | `src/attune/orchestration/meta_orchestrator.py` |
| `TaskDomain` | Task domain classification | `src/attune/orchestration/meta_orchestrator.py` |
| `CompositionPattern` | Available composition patterns (grammar rules) | `src/attune/orchestration/meta_orchestrator.py` |
| `TaskRequirements` | Extracted requirements from task analysis | `src/attune/orchestration/meta_orchestrator.py` |
| `ExecutionPlan` | Plan for agent execution | `src/attune/orchestration/meta_orchestrator.py` |
| `MetaOrchestrator` | Intelligent task analyzer and agent composition engine | `src/attune/orchestration/meta_orchestrator.py` |
| `LearningStore` | Memory + file storage for learning data | `src/attune/orchestration/pattern_learner.py` |
| `PatternRecommendation` | Pattern recommendation | `src/attune/orchestration/pattern_learner.py` |
| `PatternRecommender` | Hybrid recommendation engine for patterns | `src/attune/orchestration/pattern_learner.py` |
| `PatternLearner` | Main interface for the learning grammar system | `src/attune/orchestration/pattern_learner.py` |
| `ExecutionRecord` | Record of a single pattern execution | `src/attune/orchestration/pattern_learner_models.py` |
| `PatternStats` | Aggregated statistics for a pattern | `src/attune/orchestration/pattern_learner_models.py` |
| `ContextSignature` | Signature of a context for similarity matching | `src/attune/orchestration/pattern_learner_models.py` |
| `DynamicTeamBuilder` | Builds runnable ``DynamicTeam`` instances from various sources | `src/attune/orchestration/team_builder.py` |
| `TeamSpecification` | Specification for a dynamic agent team | `src/attune/orchestration/team_store.py` |
| `TeamStore` | Persistent storage for team specifications | `src/attune/orchestration/team_store.py` |
| `ArchitectureReport` | Architecture analysis report | `src/attune/orchestration/tools/architecture.py` |
| `RealArchitectureAnalyzer` | Static architecture analysis for Python projects | `src/attune/orchestration/tools/architecture.py` |
| `PerformanceReport` | Performance profiling report from AST-based analysis | `src/attune/orchestration/tools/performance.py` |
| `RealPerformanceProfiler` | AST-based static performance analysis | `src/attune/orchestration/tools/performance.py` |
| `QualityReport` | Code quality report from ruff and mypy | `src/attune/orchestration/tools/quality.py` |
| `RealCodeQualityAnalyzer` | Code quality analysis using ruff and mypy | `src/attune/orchestration/tools/quality.py` |
| `DocumentationReport` | Documentation completeness report | `src/attune/orchestration/tools/quality.py` |
| `RealDocumentationAnalyzer` | Documentation completeness analysis by scanning docstrings | `src/attune/orchestration/tools/quality.py` |
| `SecurityReport` | Security audit report from bandit | `src/attune/orchestration/tools/security.py` |
| `RealSecurityAuditor` | Security audit using bandit | `src/attune/orchestration/tools/security.py` |
| `RealTestGenerator` | Test code generation using LLM | `src/attune/orchestration/tools/test_generation.py` |
| `CoverageReport` | Coverage analysis report from pytest-cov | `src/attune/orchestration/tools/testing.py` |
| `RealCoverageAnalyzer` | Pytest coverage analysis | `src/attune/orchestration/tools/testing.py` |
| `RealTestGenerator` | Test code generation using LLM | `src/attune/orchestration/tools/testing.py` |
| `RealTestValidator` | Validates generated tests by running them | `src/attune/orchestration/tools/testing.py` |
| `WorkflowAgentAdapter` | Adapts a BaseWorkflow to the ``SDKAgent.process()`` interface | `src/attune/orchestration/workflow_agent_adapter.py` |
| `WorkflowComposer` | Composes ``BaseWorkflow`` subclasses into a ``DynamicTeam`` | `src/attune/orchestration/workflow_composer.py` |

## AgentTask Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `task_id` | `str` |  | Unique task identifier |
| `task_type` | `str` |  | Type of task |
| `description` | `str` |  | Task description |
| `assigned_to` | `str | None` | `None` | Agent ID assigned to task |
| `status` | `str` | `'pending'` | Current task status |
| `priority` | `int` | `5` | Task priority level |
| `created_at` | `datetime` | `field(default_factory=datetime.now)` | Task creation timestamp |
| `context` | `dict[str, Any]` | `field(default_factory=dict)` | Task context data |
| `result` | `dict[str, Any] | None` | `None` | Task execution result |

## ResolutionResult Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `winning_pattern` | `Pattern` |  | Pattern selected as winner |
| `losing_patterns` | `list[Pattern]` |  | Patterns that were not selected |
| `strategy_used` | `ResolutionStrategy` |  | Strategy used for resolution |
| `confidence` | `float` |  | Confidence in resolution decision |
| `reasoning` | `str` |  | Human-readable reasoning |
| `factors` | `dict[str, float]` | `field(default_factory=dict)` | Factors that influenced decision |

## TeamPriorities Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `readability_weight` | `float` | `0.3` | Weight for readability in scoring |
| `performance_weight` | `float` | `0.2` | Weight for performance in scoring |
| `security_weight` | `float` | `0.3` | Weight for security in scoring |
| `maintainability_weight` | `float` | `0.2` | Weight for maintainability in scoring |
| `type_preferences` | `dict[str, float]` | `field(default_factory=lambda: {'security': 1.0, 'best_practice': 0.8, 'performance': 0.7, 'style': 0.5, 'warning': 0.6})` | Preferences by pattern type |
| `preferred_tags` | `list[str]` | `field(default_factory=list)` | Tags that receive priority |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_strategy` | `strategy_name: str` | `ExecutionStrategy` | Get strategy instance by name |
| `register_strategy` | `name: str, strategy_class: type[ExecutionStrategy]` | `None` | Register a strategy class by name |
| `register_workflow` | `workflow: WorkflowDefinition` | `None` | Register a workflow for nested references |
| `get_workflow` | `workflow_id: str` | `WorkflowDefinition` | Get a registered workflow by ID |
| `get_template` | `template_id: str` | `AgentTemplate | None` | Retrieve template by ID |
| `get_all_templates` |  | `list[AgentTemplate]` | Retrieve all registered templates |
| `get_templates_by_capability` | `capability: str` | `list[AgentTemplate]` | Retrieve templates with a specific capability |
| `get_templates_by_tier` | `tier: str` | `list[AgentTemplate]` | Retrieve templates preferring a specific tier |
| `register_custom_template` | `template: AgentTemplate` | `None` | Register a user-defined template at runtime |
| `unregister_template` | `template_id: str` | `bool` | Remove a template from the registry |
| `get_registry` |  |  | Return a read-only snapshot of the template registry |
| `get_learner` |  |  | Get the default pattern learner instance |

## Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `get_strategy` | `ValueError` | 'Unknown strategy: {...}. Available: {...}' |
| `get_workflow` | `ValueError` | 'Unknown workflow: {...}. Available: {...}' |

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

## Tags

`orchestration`, `teams`
