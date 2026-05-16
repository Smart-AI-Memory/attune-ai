---
type: reference
name: orchestration-reference
feature: orchestration
depth: reference
generated_at: 2026-05-16T06:14:24.014903+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Orchestration reference

Compose agents into dynamic teams, select and register execution strategies, and manage agent templates.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ToolEnhancedStrategy` | Single agent with comprehensive tool access. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `PromptCachedSequentialStrategy` | Sequential execution with shared cached context. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `DelegationChainStrategy` | Hierarchical delegation with max depth enforcement. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `ExecutionStrategy` | Base class for agent composition strategies. | `src/attune/orchestration/_strategies/base.py` |
| `ConditionalStrategy` | Conditional branching (if X then A else B). | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `MultiConditionalStrategy` | Multiple conditional branches (switch/case pattern). | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `NestedStrategy` | Nested workflow execution (sentences within sentences). | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `StepDefinition` | Definition of a step in NestedSequentialStrategy. | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `NestedSequentialStrategy` | Sequential execution with nested workflow support. | `src/attune/orchestration/_strategies/conditional_strategies.py` |
| `ConditionType` | Type of condition for gate evaluation. | `src/attune/orchestration/_strategies/conditions.py` |
| `Condition` | A conditional gate for branching in agent workflows. | `src/attune/orchestration/_strategies/conditions.py` |
| `Branch` | A branch in conditional execution. | `src/attune/orchestration/_strategies/conditions.py` |
| `ConditionEvaluator` | Evaluates conditions against execution context. | `src/attune/orchestration/_strategies/conditions.py` |
| `SequentialStrategy` | Sequential composition (A → B → C). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `ParallelStrategy` | Parallel composition (A \|\| B \|\| C). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `DebateStrategy` | Debate/Consensus composition (A ⇄ B ⇄ C → Synthesis). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `TeachingStrategy` | Teaching/Validation (Junior → Expert Review). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `RefinementStrategy` | Progressive Refinement (Draft → Review → Polish). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `AdaptiveStrategy` | Adaptive Routing (Classifier → Specialist). | `src/attune/orchestration/_strategies/core_strategies.py` |
| `AgentResult` | Result from agent execution. | `src/attune/orchestration/_strategies/data_classes.py` |
| `StrategyResult` | Aggregated result from strategy execution. | `src/attune/orchestration/_strategies/data_classes.py` |
| `WorkflowReference` | Reference to a workflow for nested composition. | `src/attune/orchestration/_strategies/nesting.py` |
| `InlineWorkflow` | Inline workflow definition for nested composition. | `src/attune/orchestration/_strategies/nesting.py` |
| `NestingContext` | Tracks nesting depth and prevents infinite recursion. | `src/attune/orchestration/_strategies/nesting.py` |
| `WorkflowDefinition` | A registered workflow definition. | `src/attune/orchestration/_strategies/nesting.py` |
| `SDKExecutionMode` | How the agent should run. | `src/attune/orchestration/agent_models.py` |
| `SDKAgentResult` | Result from a single agent execution. | `src/attune/orchestration/agent_models.py` |
| `QualityGate` | A named threshold that an agent result must satisfy. | `src/attune/orchestration/agent_models.py` |
| `AgentLike` | Protocol for objects that can participate in DynamicTeam execution. | `src/attune/orchestration/agent_models.py` |
| `StubAgent` | Lightweight agent stub for DynamicTeam composition. | `src/attune/orchestration/agent_models.py` |
| `AgentCapability` | Capability that an agent can perform. | `src/attune/orchestration/agent_templates/models.py` |
| `ResourceRequirements` | Resource requirements for agent execution. | `src/attune/orchestration/agent_templates/models.py` |
| `AgentTemplate` | Reusable agent archetype. | `src/attune/orchestration/agent_templates/models.py` |
| `AgentConfiguration` | Saved configuration for a successful agent team composition. | `src/attune/orchestration/config_store.py` |
| `ConfigurationStore` | Persistent storage for successful agent team compositions. | `src/attune/orchestration/config_store.py` |
| `DynamicTeamResult` | Aggregated result from a DynamicTeam execution. | `src/attune/orchestration/dynamic_team.py` |
| `DynamicTeam` | Executes a dynamically-composed agent team. | `src/attune/orchestration/dynamic_team.py` |
| `TaskAnalysisMixin` | Mixin providing task analysis and agent selection for meta-orchestrator. | `src/attune/orchestration/meta_orch_analysis.py` |
| `EstimationMixin` | Mixin providing cost and duration estimation for meta-orchestrator. | `src/attune/orchestration/meta_orch_estimation.py` |
| `InteractiveModeMixin` | Mixin providing interactive mode for meta-orchestrator. | `src/attune/orchestration/meta_orch_interactive.py` |
| `TaskComplexity` | Task complexity classification. | `src/attune/orchestration/meta_orchestrator.py` |
| `TaskDomain` | Task domain classification. | `src/attune/orchestration/meta_orchestrator.py` |
| `CompositionPattern` | Available composition patterns (grammar rules). | `src/attune/orchestration/meta_orchestrator.py` |
| `TaskRequirements` | Extracted requirements from task analysis. | `src/attune/orchestration/meta_orchestrator.py` |
| `ExecutionPlan` | Plan for agent execution. | `src/attune/orchestration/meta_orchestrator.py` |
| `MetaOrchestrator` | Intelligent task analyzer and agent composition engine. | `src/attune/orchestration/meta_orchestrator.py` |
| `LearningStore` | Memory and file storage for learning data. | `src/attune/orchestration/pattern_learner.py` |
| `PatternRecommendation` | A pattern recommendation. | `src/attune/orchestration/pattern_learner.py` |
| `PatternRecommender` | Hybrid recommendation engine for patterns. | `src/attune/orchestration/pattern_learner.py` |
| `PatternLearner` | Main interface for the learning grammar system. | `src/attune/orchestration/pattern_learner.py` |
| `ExecutionRecord` | Record of a single pattern execution. | `src/attune/orchestration/pattern_learner_models.py` |
| `PatternStats` | Aggregated statistics for a pattern. | `src/attune/orchestration/pattern_learner_models.py` |
| `ContextSignature` | Signature of a context for similarity matching. | `src/attune/orchestration/pattern_learner_models.py` |
| `DynamicTeamBuilder` | Builds runnable `DynamicTeam` instances from various sources. | `src/attune/orchestration/team_builder.py` |
| `TeamSpecification` | Specification for a dynamic agent team. | `src/attune/orchestration/team_store.py` |
| `TeamStore` | Persistent storage for team specifications. | `src/attune/orchestration/team_store.py` |
| `ArchitectureReport` | Architecture analysis report. | `src/attune/orchestration/tools/architecture.py` |
| `RealArchitectureAnalyzer` | Static architecture analysis for Python projects. | `src/attune/orchestration/tools/architecture.py` |
| `PerformanceReport` | Performance profiling report from AST-based analysis. | `src/attune/orchestration/tools/performance.py` |
| `RealPerformanceProfiler` | Runs real performance profiling via AST-based static analysis. | `src/attune/orchestration/tools/performance.py` |
| `QualityReport` | Code quality report from ruff and mypy. | `src/attune/orchestration/tools/quality.py` |
| `RealCodeQualityAnalyzer` | Runs real code quality analysis using ruff and mypy. | `src/attune/orchestration/tools/quality.py` |
| `DocumentationReport` | Documentation completeness report. | `src/attune/orchestration/tools/quality.py` |
| `RealDocumentationAnalyzer` | Analyzes documentation completeness by scanning docstrings. | `src/attune/orchestration/tools/quality.py` |
| `SecurityReport` | Security audit report from bandit. | `src/attune/orchestration/tools/security.py` |
| `RealSecurityAuditor` | Runs real security audit using bandit. | `src/attune/orchestration/tools/security.py` |
| `RealTestGenerator` | Generates actual test code using LLM. | `src/attune/orchestration/tools/test_generation.py` |
| `CoverageReport` | Coverage analysis report from pytest-cov. | `src/attune/orchestration/tools/testing.py` |
| `RealCoverageAnalyzer` | Runs real pytest coverage analysis. | `src/attune/orchestration/tools/testing.py` |
| `RealTestValidator` | Validates generated tests by running them. | `src/attune/orchestration/tools/testing.py` |
| `WorkflowAgentAdapter` | Adapts a BaseWorkflow to the `SDKAgent.process()` interface. | `src/attune/orchestration/workflow_agent_adapter.py` |
| `WorkflowComposer` | Composes `BaseWorkflow` subclasses into a `DynamicTeam`. | `src/attune/orchestration/workflow_composer.py` |

## `StepDefinition` fields

`StepDefinition` is a dataclass that defines a single step in `NestedSequentialStrategy`.

| Field | Type | Default |
|-------|------|---------|
| `agent` | `AgentTemplate \| None` | `None` |
| `workflow_ref` | `WorkflowReference \| None` | `None` |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_strategy` | `strategy_name: str` | `ExecutionStrategy` | Get strategy instance by name. |
| `register_strategy` | `name: str, strategy_class: type[ExecutionStrategy]` | `None` | Register a strategy class by name. |
| `register_workflow` | `workflow: WorkflowDefinition` | `None` | Register a workflow for nested references. |
| `get_workflow` | `workflow_id: str` | `WorkflowDefinition` | Get a registered workflow by ID. |
| `get_template` | `template_id: str` | `AgentTemplate \| None` | Retrieve template by ID. |
| `get_all_templates` | — | `list[AgentTemplate]` | Retrieve all registered templates. |
| `get_templates_by_capability` | `capability: str` | `list[AgentTemplate]` | Retrieve templates with a specific capability. |
| `get_templates_by_tier` | `tier: str` | `list[AgentTemplate]` | Retrieve templates preferring a specific tier. |
| `register_custom_template` | `template: AgentTemplate` | `None` | Register a user-defined template at runtime. |
| `unregister_template` | `template_id: str` | `bool` | Remove a template from the registry. |
| `get_registry` | — | `dict[str, AgentTemplate]` | Return a read-only snapshot of the template registry. |
| `get_learner` | — | `PatternLearner` | Get the default pattern learner instance. |

### Raises

| Function | Raises | Message |
|----------|--------|---------|
| `get_strategy` | `ValueError` | `'Unknown strategy: {...}. Available: {...}'` |
| `get_workflow` | `ValueError` | `'Unknown workflow: {...}. Available: {...}'` |

### `unregister_template` return values

`unregister_template` returns `bool`. When the template ID is not found in the registry, the function returns `False`.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

## Tags

`orchestration`, `teams`
