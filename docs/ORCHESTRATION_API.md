---
description: Meta-Orchestration API Reference — task analysis, agent templates, composition patterns, execution strategies, dynamic teams, and workflow composition.
---

# Meta-Orchestration API Reference

**Version:** 8.0.1
**Last Updated:** June 9, 2026

---

## Table of Contents

1. [Core Components](#core-components)
2. [Agent Templates](#agent-templates)
3. [Meta-Orchestrator](#meta-orchestrator)
4. [Execution Strategies](#execution-strategies)
5. [Configuration Store](#configuration-store)
6. [Dynamic Teams](#dynamic-teams)
7. [Workflow Composition](#workflow-composition)
8. [Agent State Persistence](#agent-state-persistence)
9. [Workflows](#workflows)

---

## Core Components

### Overview

The meta-orchestration system is organized into the following modules:

```text
attune.orchestration/
├── agent_templates/             # Agent archetypes and capabilities (14 templates)
├── meta_orchestrator.py         # Task analysis and agent selection
├── execution_strategies.py      # 10 composition patterns (13 strategy classes)
├── _strategies/                 # Strategy implementations + registry
├── config_store.py              # Learning and memory system
├── dynamic_team.py              # Dynamic team execution (parallel/sequential/two_phase)
├── team_builder.py              # Build teams from specs, plans, or saved configs
├── team_store.py                # Persistent team configuration storage
├── workflow_agent_adapter.py    # Wrap workflows as agents for team composition
├── workflow_composer.py         # Compose workflows into DynamicTeam instances
├── pattern_learner.py           # Learn successful composition patterns
└── __init__.py
```

---

## Agent Templates

**Module:** `attune.orchestration.agent_templates`

### Classes

#### `AgentCapability`

**Dataclass representing a capability that an agent can perform.**

```python
@dataclass(frozen=True)
class AgentCapability:
    name: str
    description: str
    required_tools: list[str] = field(default_factory=list)
```

**Attributes:**
- `name` (str): Capability identifier (e.g., "analyze_gaps")
- `description` (str): Human-readable description
- `required_tools` (list[str]): List of tools needed for this capability

**Example:**
```python
cap = AgentCapability(
    name="analyze_gaps",
    description="Identify test coverage gaps",
    required_tools=["coverage_analyzer"]
)
```

---

#### `ResourceRequirements`

**Dataclass defining resource limits for agent execution.**

```python
@dataclass(frozen=True)
class ResourceRequirements:
    min_tokens: int = 1000
    max_tokens: int = 10000
    timeout_seconds: int = 300
    memory_mb: int = 512
```

**Attributes:**
- `min_tokens` (int): Minimum token budget required
- `max_tokens` (int): Maximum token budget allowed
- `timeout_seconds` (int): Maximum execution time in seconds
- `memory_mb` (int): Maximum memory usage in megabytes

**Validation:**
- `min_tokens` must be ≥ 0
- `max_tokens` must be ≥ `min_tokens`
- `timeout_seconds` must be > 0
- `memory_mb` must be > 0

**Example:**
```python
req = ResourceRequirements(
    min_tokens=2000,
    max_tokens=15000,
    timeout_seconds=600,
    memory_mb=1024
)
```

---

#### `AgentTemplate`

**Dataclass representing a reusable agent archetype.**

```python
@dataclass(frozen=True)
class AgentTemplate:
    id: str
    role: str
    capabilities: list[str]
    tier_preference: str
    tools: list[str]
    default_instructions: str
    quality_gates: dict[str, Any]
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)

    ALLOWED_TIERS = {"CHEAP", "CAPABLE", "PREMIUM"}
```

**Attributes:**
- `id` (str): Unique template identifier
- `role` (str): Human-readable agent role
- `capabilities` (list[str]): List of capability names
- `tier_preference` (str): Preferred tier ("CHEAP", "CAPABLE", "PREMIUM")
- `tools` (list[str]): List of tool identifiers
- `default_instructions` (str): Default instructions for the agent
- `quality_gates` (dict[str, Any]): Quality gate thresholds
- `resource_requirements` (ResourceRequirements): Resource limits

**Validation:**
- `id` and `role` must be non-empty strings
- `capabilities` must be non-empty list of strings
- `tier_preference` must be in `ALLOWED_TIERS`
- `tools` must be list (can be empty)
- `default_instructions` must be non-empty string
- `quality_gates` must be dict

**Example:**
```python
template = AgentTemplate(
    id="test_coverage_analyzer",
    role="Test Coverage Expert",
    capabilities=["analyze_gaps", "suggest_tests"],
    tier_preference="CAPABLE",
    tools=["coverage_analyzer", "ast_parser"],
    default_instructions="Analyze test coverage...",
    quality_gates={"min_coverage": 80}
)
```

---

### Functions

#### `get_template(template_id: str) -> AgentTemplate | None`

**Retrieve agent template by ID.**

**Parameters:**
- `template_id` (str): Template identifier

**Returns:**
- `AgentTemplate | None`: Template if found, None otherwise

**Example:**
```python
template = get_template("test_coverage_analyzer")
if template:
    print(template.role)  # "Test Coverage Expert"
```

---

#### `get_all_templates() -> list[AgentTemplate]`

**Retrieve all registered templates.**

**Returns:**
- `list[AgentTemplate]`: List of all available templates

**Example:**
```python
templates = get_all_templates()
print(f"Available: {len(templates)} templates")
for t in templates:
    print(f"  - {t.id}: {t.role}")
```

---

#### `get_templates_by_capability(capability: str) -> list[AgentTemplate]`

**Retrieve templates with a specific capability.**

**Parameters:**
- `capability` (str): Capability name to search for

**Returns:**
- `list[AgentTemplate]`: Templates with that capability

**Example:**
```python
templates = get_templates_by_capability("vulnerability_scan")
# Returns: [security_auditor]
```

---

#### `get_templates_by_tier(tier: str) -> list[AgentTemplate]`

**Retrieve templates preferring a specific tier.**

**Parameters:**
- `tier` (str): Tier name ("CHEAP", "CAPABLE", "PREMIUM")

**Returns:**
- `list[AgentTemplate]`: Templates preferring that tier

**Example:**
```python
cheap_templates = get_templates_by_tier("CHEAP")
# e.g. [documentation_writer, test_validator, report_generator]

capable_templates = get_templates_by_tier("CAPABLE")
# e.g. [test_coverage_analyzer, code_reviewer, performance_optimizer, ...]
```

---

### Pre-built Templates

**14 templates available:**

1. `test_coverage_analyzer` (CAPABLE)
2. `security_auditor` (PREMIUM)
3. `code_reviewer` (CAPABLE)
4. `documentation_writer` (CHEAP)
5. `performance_optimizer` (CAPABLE)
6. `architecture_analyst` (PREMIUM)
7. `refactoring_specialist` (CAPABLE)
8. `test_generator` (CAPABLE)
9. `test_validator` (CHEAP)
10. `report_generator` (CHEAP)
11. `documentation_analyst` (CAPABLE)
12. `synthesizer` (CAPABLE)
13. `code_simplifier` (CAPABLE)
14. `generic_agent` (CAPABLE)

---

## Meta-Orchestrator

**Module:** `attune.orchestration.meta_orchestrator`

### Enums

#### `TaskComplexity`

**Task complexity classification.**

```python
class TaskComplexity(Enum):
    SIMPLE = "simple"      # Single agent, straightforward
    MODERATE = "moderate"  # 2-3 agents, some coordination
    COMPLEX = "complex"    # 4+ agents, multi-phase execution
```

---

#### `TaskDomain`

**Task domain classification.**

```python
class TaskDomain(Enum):
    TESTING = "testing"
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    REFACTORING = "refactoring"
    GENERAL = "general"
```

---

#### `CompositionPattern`

**Available composition patterns (grammar rules).**

```python
class CompositionPattern(Enum):
    SEQUENTIAL = "sequential"  # A → B → C
    PARALLEL = "parallel"      # A ‖ B ‖ C
    DEBATE = "debate"          # A ⇄ B ⇄ C → Synthesis
    TEACHING = "teaching"      # Junior → Expert validation
    REFINEMENT = "refinement"  # Draft → Review → Polish
    ADAPTIVE = "adaptive"      # Classifier → Specialist
    CONDITIONAL = "conditional"  # If-then-else routing
    # Anthropic-inspired patterns (8-10)
    TOOL_ENHANCED = "tool_enhanced"  # Single agent with tools
    PROMPT_CACHED_SEQUENTIAL = "prompt_cached_sequential"  # Shared cached context
    DELEGATION_CHAIN = "delegation_chain"  # Hierarchical delegation (≤3 levels)
```

---

### Dataclasses

#### `TaskRequirements`

**Extracted requirements from task analysis.**

```python
@dataclass
class TaskRequirements:
    complexity: TaskComplexity
    domain: TaskDomain
    capabilities_needed: list[str]
    parallelizable: bool = False
    quality_gates: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
```

**Attributes:**
- `complexity` (TaskComplexity): Task complexity level
- `domain` (TaskDomain): Primary task domain
- `capabilities_needed` (list[str]): Required capabilities
- `parallelizable` (bool): Whether task can be parallelized
- `quality_gates` (dict[str, Any]): Quality thresholds
- `context` (dict[str, Any]): Additional context

---

#### `ExecutionPlan`

**Plan for agent execution.**

```python
@dataclass
class ExecutionPlan:
    agents: list[AgentTemplate]
    strategy: CompositionPattern
    quality_gates: dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 0.0
    estimated_duration: int = 0
```

**Attributes:**
- `agents` (list[AgentTemplate]): Agents to execute
- `strategy` (CompositionPattern): Composition pattern
- `quality_gates` (dict[str, Any]): Quality thresholds
- `estimated_cost` (float): Estimated execution cost (arbitrary units)
- `estimated_duration` (int): Estimated time in seconds

---

### Classes

#### `MetaOrchestrator`

**Intelligent task analyzer and agent composition engine.**

```python
class MetaOrchestrator:
    def __init__(self): ...

    def analyze_task(
        self, task: str, context: dict[str, Any] | None = None
    ) -> TaskRequirements: ...

    def create_execution_plan(
        self,
        requirements: TaskRequirements,
        agents: list[AgentTemplate],
        strategy: CompositionPattern,
    ) -> ExecutionPlan: ...

    def analyze_and_compose(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        interactive: bool = False,
    ) -> ExecutionPlan: ...

    def compose_team(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        state_store: Any | None = None,
        redis_client: Any | None = None,
    ) -> Any: ...
```

**Methods:**

##### `__init__()`

**Initialize meta-orchestrator.**

**Example:**
```python
orchestrator = MetaOrchestrator()
```

---

##### `analyze_task(task: str, context: dict[str, Any] | None = None) -> TaskRequirements`

**Classify a task into structured requirements** (complexity, domain,
capabilities needed) without selecting agents. Useful when you want to
inspect or adjust requirements before composing a plan.

**Returns:**
- `TaskRequirements`: complexity, domain, capabilities, parallelizability

---

##### `create_execution_plan(requirements, agents, strategy) -> ExecutionPlan`

**Assemble an `ExecutionPlan` from already-resolved requirements,
selected agents, and a composition pattern.** Used internally by
`analyze_and_compose`, but exposed for callers that select agents
themselves.

**Parameters:**
- `requirements` (TaskRequirements): Task requirements with quality gates
- `agents` (list[AgentTemplate]): Selected agents for execution
- `strategy` (CompositionPattern): Composition pattern to use

**Returns:**
- `ExecutionPlan`: Plan with agents, strategy, and cost/duration estimates

---

##### `analyze_and_compose(task, context=None, interactive=False) -> ExecutionPlan`

**Analyze task and create execution plan.**

This is the main entry point for meta-orchestration.

**Parameters:**
- `task` (str): Task description (e.g., "Boost test coverage to 90%")
- `context` (dict[str, Any] | None): Optional context dictionary
- `interactive` (bool): If `True`, prompts the user to disambiguate
  low-confidence classifications (default `False`)

**Returns:**
- `ExecutionPlan`: Plan with agents and strategy

**Raises:**
- `ValueError`: If task is invalid (empty or not a string)

**Example:**
```python
orchestrator = MetaOrchestrator()

plan = orchestrator.analyze_and_compose(
    task="Boost test coverage to 90%",
    context={"current_coverage": 75.0},
)

print(f"Agents: {[a.id for a in plan.agents]}")
print(f"Strategy: {plan.strategy.value}")
print(f"Cost: {plan.estimated_cost}")
print(f"Duration: {plan.estimated_duration}s")
```

> **Note:** the returned `ExecutionPlan` carries `agents`, `strategy`,
> `quality_gates`, `estimated_cost`, and `estimated_duration`. The
> task's `complexity`/`domain` classification lives on the
> `TaskRequirements` returned by `analyze_task`, not on `ExecutionPlan`.

**Algorithm:**
1. Classify task complexity (simple/moderate/complex)
2. Classify task domain (testing/security/etc.)
3. Extract required capabilities
4. Select appropriate agents
5. Choose composition pattern
6. Estimate cost and duration

---

##### `compose_team(task, context=None, state_store=None, redis_client=None)`

**End-to-end convenience: analyze the task and build a runnable team**
(rather than just a plan). Optionally wires in an `AgentStateStore` and
a Redis client for persistence.

**Parameters:**
- `task` (str): Task description
- `context` (dict[str, Any] | None): Optional context dictionary
- `state_store` (Any | None): Optional agent state store
- `redis_client` (Any | None): Optional Redis client for persistence

---

## Execution Strategies

**Module:** `attune.orchestration.execution_strategies`

### Dataclasses

#### `AgentResult`

**Result from agent execution.**

```python
@dataclass
class AgentResult:
    agent_id: str
    success: bool
    output: dict[str, Any]
    confidence: float = 0.0
    duration_seconds: float = 0.0
    error: str = ""
```

**Attributes:**
- `agent_id` (str): ID of agent that produced result
- `success` (bool): Whether execution succeeded
- `output` (dict[str, Any]): Agent output data
- `confidence` (float): Confidence score (0-1)
- `duration_seconds` (float): Execution time
- `error` (str): Error message if failed

---

#### `StrategyResult`

**Aggregated result from strategy execution.**

```python
@dataclass
class StrategyResult:
    success: bool
    outputs: list[AgentResult]
    aggregated_output: dict[str, Any]
    total_duration: float = 0.0
    errors: list[str] = None
```

**Attributes:**
- `success` (bool): Whether overall execution succeeded
- `outputs` (list[AgentResult]): Individual agent results
- `aggregated_output` (dict[str, Any]): Combined/synthesized output
- `total_duration` (float): Total execution time
- `errors` (list[str]): List of errors encountered

---

### Base Class

#### `ExecutionStrategy`

**Base class for agent composition strategies.**

```python
class ExecutionStrategy(ABC):
    @abstractmethod
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Methods:**

##### `execute(agents: list[AgentTemplate], context: dict[str, Any]) -> StrategyResult`

**Execute agents using this strategy.**

**Parameters:**
- `agents` (list[AgentTemplate]): Agents to execute
- `context` (dict[str, Any]): Initial context

**Returns:**
- `StrategyResult`: Aggregated results

**Raises:**
- `ValueError`: If agents list is empty
- `TimeoutError`: If execution exceeds timeout

---

### Strategy Classes

#### `SequentialStrategy`

**Sequential composition (A → B → C).**

```python
class SequentialStrategy(ExecutionStrategy):
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Behavior:**
- Executes agents one after another
- Each agent receives output from previous agent in context
- Total duration = sum of individual durations

**Example:**
```python
strategy = SequentialStrategy()
result = await strategy.execute(
    [analyzer, generator, validator],
    {"project_root": "./"}
)
```

---

#### `ParallelStrategy`

**Parallel composition (A ‖ B ‖ C).**

```python
class ParallelStrategy(ExecutionStrategy):
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Behavior:**
- Executes all agents simultaneously using `asyncio.gather()`
- Each agent receives same initial context
- Total duration = max individual duration

**Example:**
```python
strategy = ParallelStrategy()
result = await strategy.execute(
    [security, coverage, quality, docs],
    {"path": "."}
)
```

---

#### `DebateStrategy`

**Debate/Consensus composition (A ⇄ B ⇄ C → Synthesis).**

```python
class DebateStrategy(ExecutionStrategy):
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Behavior:**
- Phase 1: Agents provide independent opinions (parallel)
- Phase 2: Synthesizer aggregates and resolves conflicts
- Total duration ≈ 2x max individual duration

**Output structure:**
```python
{
    "debate_participants": ["agent1", "agent2"],
    "opinions": [output1, output2],
    "consensus": {
        "consensus_reached": True,
        "success_votes": 2,
        "total_votes": 2,
        "avg_confidence": 0.85
    }
}
```

**Example:**
```python
strategy = DebateStrategy()
result = await strategy.execute(
    [architect1, architect2, architect3],
    {"requirements": {...}}
)
```

---

#### `TeachingStrategy`

**Teaching/Validation (Junior → Expert Review).**

```python
class TeachingStrategy(ExecutionStrategy):
    def __init__(self, quality_threshold: float = 0.7): ...

    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Parameters:**
- `quality_threshold` (float): Minimum confidence for junior to pass (0-1), default 0.7

**Behavior:**
- Phase 1: Junior agent attempts task
- Phase 2: Quality gate checks confidence
- Phase 3: Expert takes over if junior fails

**Requirements:**
- Exactly 2 agents: `[junior, expert]`

**Output structure:**
```python
{
    "outcome": "junior_success",  # or "expert_takeover"
    "junior_output": {...},
    "expert_output": {...}  # only if expert took over
}
```

**Example:**
```python
strategy = TeachingStrategy(quality_threshold=0.7)
result = await strategy.execute(
    [junior_writer, expert_writer],
    {"topic": "API documentation"}
)
```

---

#### `RefinementStrategy`

**Progressive Refinement (Draft → Review → Polish).**

```python
class RefinementStrategy(ExecutionStrategy):
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Behavior:**
- Each agent refines output from previous stage
- Sequential execution with progressive quality improvement
- Stops on first failure

**Requirements:**
- At least 2 agents (typically 3: drafter, reviewer, polisher)

**Output structure:**
```python
{
    "refinement_stages": 3,
    "final_output": {...},
    "stage_outputs": [draft, reviewed, polished]
}
```

**Example:**
```python
strategy = RefinementStrategy()
result = await strategy.execute(
    [drafter, reviewer, polisher],
    {"requirements": {...}}
)
```

---

#### `AdaptiveStrategy`

**Adaptive Routing (Classifier → Specialist).**

```python
class AdaptiveStrategy(ExecutionStrategy):
    async def execute(
        self, agents: list[AgentTemplate], context: dict[str, Any]
    ) -> StrategyResult: ...
```

**Behavior:**
- Phase 1: Classifier assesses task complexity
- Phase 2: Routes to appropriate specialist based on confidence
  - High confidence (>0.8) → CHEAP specialist
  - Low confidence (<0.8) → PREMIUM specialist

**Requirements:**
- At least 2 agents: `[classifier, specialist1, ...]`

**Output structure:**
```python
{
    "classification": {...},
    "selected_specialist": "specialist_id",
    "specialist_output": {...}
}
```

**Example:**
```python
strategy = AdaptiveStrategy()
result = await strategy.execute(
    [classifier, cheap_specialist, premium_specialist],
    {"task_description": "..."}
)
```

---

#### Conditional & Nested Strategies

These extend the core six with routing and composition:

- **`ConditionalStrategy`** — If-then-else routing: evaluate a
  condition, then run the matching branch's agents.
- **`MultiConditionalStrategy`** — Multi-way (switch-style) routing
  across several conditions.
- **`NestedStrategy`** — Run a strategy whose "agents" are themselves
  sub-strategies (compose strategies recursively).
- **`NestedSequentialStrategy`** — Sequential execution of nested
  sub-strategies.

#### Anthropic-Inspired Strategies (patterns 8–10)

- **`ToolEnhancedStrategy`** — A single agent augmented with tools.
- **`PromptCachedSequentialStrategy`** — Sequential agents sharing a
  cached prompt prefix to cut input-token cost.
- **`DelegationChainStrategy`** — Hierarchical delegation (≤3 levels):
  a lead agent delegates subtasks to specialists.

All strategy classes subclass `ExecutionStrategy` and implement the
same `async execute(agents, context) -> StrategyResult` interface.

---

### Functions

#### `get_strategy(strategy_name: str) -> ExecutionStrategy`

**Get strategy instance by name.**

**Parameters:**
- `strategy_name` (str): Strategy name (any key in `STRATEGY_REGISTRY`)

**Returns:**
- `ExecutionStrategy`: Strategy instance

**Raises:**
- `ValueError`: If strategy name is invalid

**Example:**
```python
strategy = get_strategy("parallel")
isinstance(strategy, ParallelStrategy)  # True

# Available strategies (13)
STRATEGY_REGISTRY = {
    # Core 7 patterns
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
    # Anthropic-inspired patterns (8-10)
    "tool_enhanced": ToolEnhancedStrategy,
    "prompt_cached_sequential": PromptCachedSequentialStrategy,
    "delegation_chain": DelegationChainStrategy,
}
```

---

## Configuration Store

**Module:** `attune.orchestration.config_store`

### Dataclasses

#### `AgentConfiguration`

**Saved configuration for a successful agent team composition.**

```python
@dataclass
class AgentConfiguration:
    # Identity
    id: str
    task_pattern: str

    # Team Composition
    agents: list[dict[str, Any]]
    strategy: str

    # Quality Criteria
    quality_gates: dict[str, Any]

    # Performance Metrics
    success_rate: float = 0.0
    avg_quality_score: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime | None = None
    tags: list[str] = field(default_factory=list)
```

**Attributes:**
- `id` (str): Unique configuration identifier
- `task_pattern` (str): Task pattern (e.g., "release_prep")
- `agents` (list[dict[str, Any]]): Agent configurations
- `strategy` (str): Composition pattern used
- `quality_gates` (dict[str, Any]): Quality thresholds
- `success_rate` (float): Success rate (0.0-1.0)
- `avg_quality_score` (float): Average quality score (0-100)
- `usage_count` (int): Number of times used
- `success_count` (int): Number of successes
- `failure_count` (int): Number of failures
- `created_at` (datetime): Creation timestamp
- `last_used` (datetime | None): Last usage timestamp
- `tags` (list[str]): Organizational tags

**Methods:**

##### `record_outcome(success: bool, quality_score: float) -> None`

**Record an execution outcome and update metrics.**

**Parameters:**
- `success` (bool): Whether orchestration succeeded
- `quality_score` (float): Quality score (0-100)

**Raises:**
- `ValueError`: If quality_score is out of range

**Example:**
```python
config.record_outcome(success=True, quality_score=87.5)

# Updates:
# - usage_count += 1
# - success_count += 1 (if success)
# - success_rate recalculated
# - avg_quality_score updated (weighted average)
# - last_used = now
```

---

##### `to_dict() -> dict[str, Any]`

**Serialize to dictionary for JSON storage.**

**Returns:**
- `dict[str, Any]`: Dictionary representation

**Example:**
```python
data = config.to_dict()
# Datetime objects converted to ISO format strings
```

---

##### `from_dict(data: dict[str, Any]) -> AgentConfiguration`

**Deserialize from dictionary (class method).**

**Parameters:**
- `data` (dict[str, Any]): Dictionary from JSON

**Returns:**
- `AgentConfiguration`: Configuration instance

**Example:**
```python
config = AgentConfiguration.from_dict(data)
# ISO format strings converted back to datetime objects
```

---

### Classes

#### `ConfigurationStore`

**Persistent storage for successful agent team compositions.**

```python
class ConfigurationStore:
    def __init__(
        self,
        storage_dir: str | None = None,
        pattern_library: PatternLibrary | None = None,
    ): ...
```

**Parameters:**
- `storage_dir` (str | None): Directory for storing configurations (default: `.attune/orchestration/compositions/`)
- `pattern_library` (PatternLibrary | None): Optional pattern library for integration

**Methods:**

##### `save(config: AgentConfiguration) -> Path`

**Save agent configuration to disk and update pattern library.**

**Parameters:**
- `config` (AgentConfiguration): Configuration to save

**Returns:**
- `Path`: Path to saved file

**Raises:**
- `ValueError`: If config.id is invalid or path is unsafe
- `OSError`: If file write fails

**Example:**
```python
store = ConfigurationStore()

config = AgentConfiguration(
    id="comp_001",
    task_pattern="release_prep",
    agents=[...],
    strategy="parallel",
    quality_gates={...}
)

path = store.save(config)
print(f"Saved to: {path}")
```

---

##### `load(config_id: str) -> AgentConfiguration | None`

**Load configuration by ID.**

**Parameters:**
- `config_id` (str): Configuration ID

**Returns:**
- `AgentConfiguration | None`: Configuration if found

**Raises:**
- `ValueError`: If config_id is invalid

**Example:**
```python
config = store.load("comp_001")
if config:
    print(f"Success rate: {config.success_rate:.1%}")
```

---

##### `search(...) -> list[AgentConfiguration]`

**Search for configurations matching criteria.**

```python
def search(
    self,
    task_pattern: str | None = None,
    min_success_rate: float = 0.0,
    min_quality_score: float = 0.0,
    limit: int = 10,
) -> list[AgentConfiguration]: ...
```

**Parameters:**
- `task_pattern` (str | None): Filter by task pattern
- `min_success_rate` (float): Minimum success rate (0.0-1.0)
- `min_quality_score` (float): Minimum quality score (0-100)
- `limit` (int): Maximum results

**Returns:**
- `list[AgentConfiguration]`: Matching configurations, sorted by success rate descending

**Raises:**
- `ValueError`: If parameters out of range

**Example:**
```python
matches = store.search(
    task_pattern="release_prep",
    min_success_rate=0.8,
    min_quality_score=80.0,
    limit=5
)

for config in matches:
    print(f"{config.id}: {config.success_rate:.1%}")
```

---

##### `get_best_for_task(task_pattern: str) -> AgentConfiguration | None`

**Get best-performing configuration for a task pattern.**

**Parameters:**
- `task_pattern` (str): Task pattern

**Returns:**
- `AgentConfiguration | None`: Best configuration if found

**Example:**
```python
best = store.get_best_for_task("release_prep")
if best:
    print(f"Best: {best.id} ({best.success_rate:.1%})")
```

---

##### `delete(config_id: str) -> bool`

**Delete a configuration.**

**Parameters:**
- `config_id` (str): Configuration ID

**Returns:**
- `bool`: True if deleted, False if not found

**Raises:**
- `ValueError`: If config_id is invalid
- `OSError`: If file deletion fails

**Example:**
```python
deleted = store.delete("comp_001")
print(f"Deleted: {deleted}")
```

---

##### `list_all() -> list[AgentConfiguration]`

**List all configurations.**

**Returns:**
- `list[AgentConfiguration]`: All configurations, sorted by last_used descending

**Example:**
```python
all_configs = store.list_all()
for config in all_configs:
    print(f"{config.id}: used {config.usage_count} times")
```

---

## Dynamic Teams

**Module:** `attune.orchestration.dynamic_team`

### Classes

#### `DynamicTeam`

**Executes a team of agents with configurable strategy and quality gates.**

```python
class DynamicTeam:
    def __init__(
        self,
        team_name: str,
        agents: list[SDKAgent | WorkflowAgentAdapter],
        strategy: str = "parallel",
        quality_gates: list[QualityGate] | None = None,
        phases: list[dict[str, Any]] | None = None,
    ) -> None: ...

    async def execute(self, input_data: dict[str, Any]) -> DynamicTeamResult: ...
```

**Parameters:**

- `team_name` (str): Human-readable team name
- `agents` (list): SDKAgent or WorkflowAgentAdapter instances
- `strategy` (str): Execution strategy (`parallel`, `sequential`, `two_phase`)
- `quality_gates` (list[QualityGate]): Quality thresholds to enforce
- `phases` (list[dict]): Phase definitions for `two_phase` strategy

**Strategies:**

| Strategy | Description |
|----------|-------------|
| `parallel` | Execute all agents concurrently via `asyncio.gather()` |
| `sequential` | Execute agents one after another, passing results forward |
| `two_phase` | Split agents into gatherer and reasoner phases with a gate between them |

**Example:**

```python
from attune.orchestration import DynamicTeam, DynamicTeamBuilder

builder = DynamicTeamBuilder(state_store=state_store)
team = builder.build_from_spec(spec)
result = await team.execute({"target": "src/"})

print(f"Success: {result.success}")
print(f"Quality gate results: {result.quality_gate_results}")
```

---

#### `DynamicTeamResult`

**Aggregated result from team execution.**

```python
@dataclass
class DynamicTeamResult:
    team_name: str
    strategy: str
    success: bool = True
    agent_results: list[SDKAgentResult] = field(default_factory=list)
    quality_gate_results: dict[str, bool] = field(default_factory=dict)
    total_cost: float = 0.0
    execution_time_ms: float = 0.0
    phase_results: list[dict[str, Any]] = field(default_factory=list)
```

---

### `DynamicTeamBuilder`

**Module:** `attune.orchestration.team_builder`

**Builds runnable `DynamicTeam` instances from various sources.**

```python
class DynamicTeamBuilder:
    def __init__(
        self,
        state_store: AgentStateStore | None = None,
        redis_client: Any | None = None,
    ) -> None: ...

    def build_from_spec(self, spec: TeamSpecification) -> DynamicTeam: ...
    def build_from_plan(self, plan: dict[str, Any]) -> DynamicTeam: ...
    def build_from_config(self, config: AgentConfiguration) -> DynamicTeam: ...
```

**Methods:**

- `build_from_spec()` - Build from a `TeamSpecification` dataclass
- `build_from_plan()` - Build from a `MetaOrchestrator` execution plan dict
- `build_from_config()` - Build from a saved `AgentConfiguration`

---

### `TeamStore`

**Module:** `attune.orchestration.team_store`

**Persistent storage for team specifications.**

```python
class TeamStore:
    def __init__(self, storage_dir: str | None = None) -> None: ...

    def save(self, spec: TeamSpecification) -> Path: ...
    def load(self, name: str) -> TeamSpecification | None: ...
    def list_all(self) -> list[TeamSpecification]: ...
    def delete(self, name: str) -> bool: ...
```

Storage location: `.attune/orchestration/teams/{name}.json`

---

## Workflow Composition

**Module:** `attune.orchestration.workflow_composer`

### `WorkflowComposer`

**Composes `BaseWorkflow` subclasses into a `DynamicTeam`.**

Each workflow is wrapped via `WorkflowAgentAdapter` so that the `DynamicTeam` executor can call `adapter.process(input_data)` uniformly for both SDK agents and workflows.

```python
class WorkflowComposer:
    def __init__(self, state_store: Any | None = None) -> None: ...

    def compose(
        self,
        team_name: str,
        workflows: list[dict[str, Any]],
        strategy: str = "parallel",
        quality_gates: dict[str, Any] | None = None,
        phases: list[dict[str, Any]] | None = None,
    ) -> DynamicTeam: ...
```

**Parameters (compose):**

- `team_name` (str): Human-readable name for the composed team
- `workflows` (list[dict]): Workflow specifications. Each dict must have:
  - `workflow`: A `BaseWorkflow` subclass (type)
  - `kwargs` (optional): Dict of keyword arguments for the workflow constructor
  - `role` (optional): Human-readable role name
  - `agent_id` (optional): Unique agent identifier
- `strategy` (str): Execution strategy (`parallel`, `sequential`, `two_phase`)
- `quality_gates` (dict): Quality gate specifications
- `phases` (list[dict]): Phase definitions for `two_phase` strategy

**Raises:**

- `ValueError`: If `workflows` is empty

**Example:**

```python
from attune.orchestration import WorkflowComposer

composer = WorkflowComposer(state_store=state_store)
team = composer.compose(
    team_name="comprehensive-review",
    workflows=[
        {"workflow": SecurityAuditWorkflow, "kwargs": {"cost_tracker": ct}},
        {"workflow": CodeReviewWorkflow, "kwargs": {"cost_tracker": ct}},
    ],
    strategy="parallel",
    quality_gates={"min_score": 70},
)
result = await team.execute({"target": "src/"})
```

---

### `WorkflowAgentAdapter`

**Module:** `attune.orchestration.workflow_agent_adapter`

**Adapts a `BaseWorkflow` to the `SDKAgent.process()` interface.**

```python
class WorkflowAgentAdapter:
    def __init__(
        self,
        workflow_class: type,
        workflow_kwargs: dict[str, Any] | None = None,
        agent_id: str | None = None,
        role: str | None = None,
        state_store: Any | None = None,
    ) -> None: ...

    def process(self, input_data: dict[str, Any]) -> SDKAgentResult: ...
```

Bridges the async/sync boundary using `asyncio.run()` in a thread when called from an existing event loop (same pattern as `DynamicTeam._execute_parallel()`).

---

## Agent State Persistence

**Module:** `attune.agents.state`

### `AgentStateStore`

**Persistent storage for agent execution history and checkpoints.**

```python
class AgentStateStore:
    def __init__(self, storage_dir: str | None = None) -> None: ...

    def record_start(self, agent_id: str, role: str, tier: str) -> str: ...
    def record_completion(
        self, execution_id: str, agent_id: str, findings: dict, score: float, cost: float
    ) -> None: ...
    def record_failure(self, execution_id: str, agent_id: str, error: str) -> None: ...
    def save_checkpoint(self, agent_id: str, checkpoint_data: dict) -> None: ...
    def get_last_checkpoint(self, agent_id: str) -> dict | None: ...
    def get_agent_state(self, agent_id: str) -> AgentStateRecord | None: ...
    def search_history(
        self, agent_id: str | None = None, status: str | None = None, limit: int = 50
    ) -> list[AgentExecutionRecord]: ...
```

Storage location: `.attune/agents/state/{agent_id}.json`

### `AgentRecoveryManager`

**Finds and recovers interrupted agent executions.**

```python
class AgentRecoveryManager:
    def __init__(self, state_store: AgentStateStore) -> None: ...

    def find_interrupted_agents(self) -> list[str]: ...
    def recover_agent(self, agent_id: str) -> dict | None: ...
    def mark_abandoned(self, agent_id: str) -> None: ...
```

---

## Workflows

**Module:** `attune.workflows`

> **Removed in v7.0.0.** The orchestration-specific workflow wrappers
> `OrchestratedReleasePrepWorkflow` and `TestCoverageBoostWorkflow`
> (and the `ReleaseReadinessReport` they returned) were removed in
> v7.0.0. Their functionality is covered by the standard SDK-native
> workflows registered in `attune.workflows`:
>
> - **Release preparation:** `ReleasePreparationWorkflow`
>   (`attune.workflows.release_prep`), `SecureReleasePipeline`
>   (`attune.workflows.secure_release`), and the multi-agent
>   `ReleasePrepTeamWorkflow` (`attune.agents.release`).
> - **Test coverage / generation:** the `test-gen` workflow family.
>
> Run any of them via `attune workflow run <name>` or the MCP tools.
> See the [API Reference](reference/API_REFERENCE.md) for the current
> workflow catalog, and use this document for the orchestration
> primitives (`MetaOrchestrator`, strategies, `DynamicTeam`) that those
> workflows compose with.

---

## Complete Example

**Putting it all together:**

```python
import asyncio
from attune.orchestration import get_template
from attune.orchestration.meta_orchestrator import MetaOrchestrator
from attune.orchestration.execution_strategies import get_strategy
from attune.orchestration.config_store import (
    ConfigurationStore,
    AgentConfiguration,
)

async def main():
    # Manual orchestration: analyze a task, reuse a proven
    # composition if one exists, otherwise compose a fresh plan.
    orchestrator = MetaOrchestrator()
    store = ConfigurationStore()

    # Check for proven composition
    best = store.get_best_for_task("release_prep")

    if best and best.success_rate >= 0.8:
        # Reuse proven composition
        agents = [get_template(a["role"]) for a in best.agents]
        strategy = get_strategy(best.strategy)
    else:
        # Create new composition
        plan = orchestrator.analyze_and_compose(
            task="Prepare for release",
            context={"version": "8.0.1"}
        )
        agents = plan.agents
        strategy = get_strategy(plan.strategy.value)

    # Execute
    result = await strategy.execute(agents, {"path": "."})

    # Record outcome
    if best:
        quality_score = 85.0  # Calculate from result
        best.record_outcome(result.success, quality_score)
        store.save(best)

asyncio.run(main())
```

---

## Type Hints

**All public APIs have complete type hints:**

```python
from typing import Any, Dict, List, Optional

# Aliases for backward compatibility
Context = Dict[str, Any]
AgentList = List[AgentTemplate]
QualityGates = Dict[str, Any]

# Return types
async def execute(...) -> StrategyResult: ...
def search(...) -> list[AgentConfiguration]: ...
```

---

## Error Handling

**All functions validate inputs and raise appropriate exceptions:**

```python
try:
    template = get_template("invalid_id")
except ValueError as e:
    print(f"Invalid template ID: {e}")

try:
    plan = orchestrator.analyze_and_compose("", context)
except ValueError as e:
    print(f"Invalid task: {e}")

try:
    result = await strategy.execute([], context)
except ValueError as e:
    print(f"Empty agents list: {e}")
```

---

## Next Steps

- **User Guide:** [ORCHESTRATION_USER_GUIDE.md](ORCHESTRATION_USER_GUIDE.md)
- **Examples:** [examples/orchestration/](../examples/orchestration/)
- **Source Code:** [src/attune/orchestration/](../src/attune/orchestration/)

---

**Questions?** Open an issue on [GitHub](https://github.com/Smart-AI-Memory/attune-ai/issues)
