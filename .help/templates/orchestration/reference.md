---
type: reference
feature: orchestration
depth: reference
generated_at: 2026-04-14T15:16:38.053820+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration reference

## Execution strategies

| Strategy | Parameters | Description |
|----------|------------|-------------|
| `ToolEnhancedStrategy` | `tools: list[dict[str, Any]] \| None = None` | Single agent with comprehensive tool access |
| `PromptCachedSequentialStrategy` | `cached_context: str \| None = None, cache_ttl: int = 3600` | Sequential execution with shared cached context |
| `DelegationChainStrategy` | `max_depth: int = 3` | Hierarchical delegation with max depth enforcement |
| `ExecutionStrategy` | | Base class for agent composition strategies |
| `ConditionalStrategy` | `condition: Condition, then_branch: Branch, else_branch: Branch \| None = None` | Conditional branching (if X then A else B) |
| `MultiConditionalStrategy` | `conditions: list[tuple[Condition, Branch]], default_branch: Branch \| None = None` | Multiple conditional branches (switch/case pattern) |
| `NestedStrategy` | `workflow_ref: WorkflowReference, max_depth: int = NestingContext.DEFAULT_MAX_DEPTH` | Nested workflow execution (sentences within sentences) |
| `NestedSequentialStrategy` | `steps: list[StepDefinition], max_depth: int = NestingContext.DEFAULT_MAX_DEPTH` | Sequential execution with nested workflow support |
| `SequentialStrategy` | | Sequential composition (A → B → C) |
| `ParallelStrategy` | | Parallel composition (A \|\| B \|\| C) |
| `DebateStrategy` | | Debate/Consensus composition (A ⇄ B ⇄ C → Synthesis) |
| `TeachingStrategy` | | Teaching/Validation (Junior → Expert Review) |
| `RefinementStrategy` | | Progressive Refinement (Draft → Review → Polish) |
| `AdaptiveStrategy` | | Adaptive Routing (Classifier → Specialist) |

### Strategy methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `execute` | `agents: list[AgentTemplate], context: dict[str, Any]` | `StrategyResult` | Execute the strategy with given agents and context |

## Data classes

### StepDefinition fields

| Field | Type | Default |
|-------|------|---------|
| `agent` | `AgentTemplate \| None` | `None` |
| `workflow_ref` | `WorkflowReference \| None` | `None` |

## Strategy management functions

| Function | Parameters | Returns | Description | Raises |
|----------|------------|---------|-------------|--------|
| `get_strategy` | `strategy_name: str` | `ExecutionStrategy` | Get strategy instance by name | `ValueError` — 'Unknown strategy: {...}. Available: {...}' |
| `register_strategy` | `name: str, strategy_class: type[ExecutionStrategy]` | `None` | Register a strategy class by name | |

## Workflow management functions

| Function | Parameters | Returns | Description | Raises |
|----------|------------|---------|-------------|--------|
| `register_workflow` | `workflow: WorkflowDefinition` | `None` | Register a workflow for nested references | |
| `get_workflow` | `workflow_id: str` | `WorkflowDefinition` | Get a registered workflow by ID | `ValueError` — 'Unknown workflow: {...}. Available: {...}' |

## Agent template functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_template` | `template_id: str` | `AgentTemplate \| None` | Retrieve template by ID |
| `get_all_templates` | | `list[AgentTemplate]` | Retrieve all registered templates |
| `get_templates_by_capability` | `capability: str` | `list[AgentTemplate]` | Retrieve templates with a specific capability |
| `get_templates_by_tier` | `tier: str` | `list[AgentTemplate]` | Retrieve templates preferring a specific tier |
| `register_custom_template` | `template: AgentTemplate` | `None` | Register a user-defined template at runtime |
| `unregister_template` | `template_id: str` | `bool` | Remove a template from the registry |
| `get_registry` | | | Return a read-only snapshot of the template registry |

### unregister_template return value

`False`

## Meta-orchestration classes

| Class | Description |
|-------|-------------|
| `MetaOrchestrator` | Intelligent task analyzer and agent composition engine |
| `DynamicTeam` | Executes a dynamically-composed agent team |
| `DynamicTeamBuilder` | Builds runnable `DynamicTeam` instances from various sources |
| `DynamicTeamResult` | Aggregated result from a DynamicTeam execution |
| `TaskComplexity` | Task complexity classification |
| `TaskDomain` | Task domain classification |
| `CompositionPattern` | Available composition patterns (grammar rules) |
| `TaskRequirements` | Extracted requirements from task analysis |
| `ExecutionPlan` | Plan for agent execution |

## Pattern learning classes

| Class | Description |
|-------|-------------|
| `PatternLearner` | Main interface for the learning grammar system |
| `PatternRecommender` | Hybrid recommendation engine for patterns |
| `LearningStore` | Memory + file storage for learning data |
| `PatternRecommendation` | A pattern recommendation |
| `ExecutionRecord` | Record of a single pattern execution |
| `PatternStats` | Aggregated statistics for a pattern |
| `ContextSignature` | Signature of a context for similarity matching |

## Storage and configuration classes

| Class | Description |
|-------|-------------|
| `TeamStore` | Persistent storage for team specifications |
| `TeamSpecification` | Specification for a dynamic agent team |
| `ConfigurationStore` | Persistent storage for successful agent team compositions |
| `AgentConfiguration` | Saved configuration for a successful agent team composition |

## Tool integration classes

| Class | Description |
|-------|-------------|
| `RealArchitectureAnalyzer` | Static architecture analysis for Python projects |
| `RealPerformanceProfiler` | Runs real performance profiling via AST-based static analysis |
| `RealCodeQualityAnalyzer` | Runs real code quality analysis using ruff and mypy |
| `RealDocumentationAnalyzer` | Analyzes documentation completeness by scanning docstrings |
| `RealSecurityAuditor` | Runs real security audit using bandit |
| `RealCoverageAnalyzer` | Runs real pytest coverage analysis |
| `RealTestGenerator` | Generates actual test code using LLM |
| `RealTestValidator` | Validates generated tests by running them |
| `ArchitectureReport` | Architecture analysis report |
| `PerformanceReport` | Performance profiling report from AST-based analysis |
| `QualityReport` | Code quality report from ruff and mypy |
| `DocumentationReport` | Documentation completeness report |
| `SecurityReport` | Security audit report from bandit |
| `CoverageReport` | Coverage analysis report from pytest-cov |

## Workflow integration classes

| Class | Description |
|-------|-------------|
| `WorkflowAgentAdapter` | Adapts a BaseWorkflow to the `SDKAgent.process()` interface |
| `WorkflowComposer` | Composes `BaseWorkflow` subclasses into a `DynamicTeam` |

## Coordination classes

| Class | Description |
|-------|-------------|
| `AgentCoordinator` | Redis-backed coordinator for multi-agent teams |
| `TeamSession` | A collaborative session for multiple agents working together |
| `ConflictResolver` | Resolves conflicts between patterns from different agents |
| `AgentTask` | A task assigned to an agent |
| `ResolutionStrategy` | Strategy for resolving pattern conflicts |
| `ResolutionResult` | Result of conflict resolution between patterns |
| `TeamPriorities` | Team-configured priorities for conflict resolution |

## Core data classes

| Class | Description |
|-------|-------------|
| `AgentTemplate` | Reusable agent archetype |
| `AgentCapability` | Capability that an agent can perform |
| `ResourceRequirements` | Resource requirements for agent execution |
| `AgentResult` | Result from agent execution |
| `StrategyResult` | Aggregated result from strategy execution |
| `SDKAgentResult` | Result from a single agent execution |
| `QualityGate` | A named threshold that an agent result must satisfy |
| `ConditionType` | Type of condition for gate evaluation |
| `Condition` | A conditional gate for branching in agent workflows |
| `Branch` | A branch in conditional execution |
| `ConditionEvaluator` | Evaluates conditions against execution context |

## Workflow nesting classes

| Class | Description |
|-------|-------------|
| `WorkflowReference` | Reference to a workflow for nested composition |
| `InlineWorkflow` | Inline workflow definition for nested composition |
| `NestingContext` | Tracks nesting depth and prevents infinite recursion |
| `WorkflowDefinition` | A registered workflow definition |

## Agent protocols and stubs

| Class | Description |
|-------|-------------|
| `AgentLike` | Protocol for objects that can participate in DynamicTeam execution |
| `StubAgent` | Lightweight agent stub for DynamicTeam composition |
| `SDKExecutionMode` | How the agent should run |

## Mixins

| Class | Description |
|-------|-------------|
| `TaskAnalysisMixin` | Mixin providing task analysis and agent selection for meta-orchestrator |
| `EstimationMixin` | Mixin providing cost and duration estimation for meta-orchestrator |
| `InteractiveModeMixin` | Mixin providing interactive mode for meta-orchestrator |

## Other functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_learner` | | | Get the default pattern learner instance |
