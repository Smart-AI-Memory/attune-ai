---
description: Orchestration API Reference — agent templates, execution strategies, configuration store, agent teams, and agent state persistence.
---

# Orchestration API Reference

**Version:** 11.0.0
**Last Updated:** July 29, 2026

---

## Table of Contents

1. [Core Components](#core-components)
2. [Agent Templates](#agent-templates)
3. [Execution Strategies](#execution-strategies)
4. [Configuration Store](#configuration-store)
5. [Agent Teams](#agent-teams)
6. [Agent State Persistence](#agent-state-persistence)
7. [Workflows](#workflows)

---

## Core Components

### Overview

The orchestration system is organized into the following modules:

```text
attune.orchestration/
├── agent_templates/             # Agent archetypes and capabilities (14 templates)
├── execution_strategies.py      # 10 composition patterns (13 strategy classes)
├── _strategies/                 # Strategy implementations + registry
├── config_store.py              # Learning and memory system
└── __init__.py

attune.agents/
├── team.py                      # AgentTeam: fan-out workflows + quality gates
└── state.py                     # Agent execution history and recovery
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

## Agent Teams

**Module:** `attune.agents.team`

`AgentTeam` fans several workflows out over a target, then applies
quality gates to their results. It is a fan-out + gate model: each
agent runs the same target independently and each gate checks one
agent's score against a threshold. There is no sequential, two-phase,
or DAG topology and no pluggable strategy — for ordered composition,
use the strategy classes in
[Execution Strategies](#execution-strategies) directly.

### Classes

#### `WorkflowAgent`

**Wraps a workflow class so a team can run it as one agent.**

```python
class WorkflowAgent:
    def __init__(
        self,
        key: str,
        workflow_cls: type,
        *,
        files: list[str] | None = None,
        score_fn=None,
        default_score=None,
        escalate: bool = False,
    ) -> None: ...
```

**Parameters:**

- `key` (str): Unique identifier for this agent within the team
- `workflow_cls` (type): Workflow class to run (e.g.
  `CodeReviewWorkflow`)
- `files` (list[str] | None): Files or paths the workflow scans
- `score_fn` (callable | None): Extracts a numeric score from the
  workflow result; defaults to a built-in extractor
- `default_score` (float | None): Score used when extraction fails
- `escalate` (bool): Escalate the model tier on retry

---

#### `GateSpec`

**Declares a quality gate against one agent's score.**

```python
class GateSpec:
    def __init__(
        self,
        name: str,
        agent_key: str,
        threshold: float,
        critical: bool = True,
    ) -> None: ...
```

**Parameters:**

- `name` (str): Human-readable gate name
- `agent_key` (str): Which agent's score this gate checks
- `threshold` (float): Minimum passing score
- `critical` (bool): If `True`, a failure is a blocker; otherwise a
  warning

---

#### `AgentTeam`

**Runs a list of `WorkflowAgent`s and applies the gates.**

```python
class AgentTeam:
    def __init__(
        self,
        agents: list[WorkflowAgent],
        gates: list[GateSpec],
    ) -> None: ...

    async def run(self, target: str | list[str]) -> TeamReport: ...
```

**Parameters:**

- `agents` (list[WorkflowAgent]): Agents to run
- `gates` (list[GateSpec]): Quality gates to apply to agent results

`run(target)` is async; `target` is a path string or list of paths. It
returns a `TeamReport(passed, gates, results, blockers, warnings,
cost)`, where `results` is a list of `AgentResult(key, score, cost,
success, details)`.

**Example:**

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent(
            "security-audit", SecurityAuditWorkflow, files=["src/"]
        ),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)
report = asyncio.run(team.run(["src/"]))
print(report.passed, report.blockers, report.warnings, report.cost)
```

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
> primitives (agent templates, strategies, `AgentTeam`) that those
> workflows compose with.

---

## Complete Example

**Putting it all together** — run an agent team, then record the
outcome in the configuration store for future reuse:

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow
from attune.orchestration.config_store import (
    ConfigurationStore,
    AgentConfiguration,
)

async def main():
    team = AgentTeam(
        agents=[
            WorkflowAgent(
                "code-review", CodeReviewWorkflow, files=["src/"]
            ),
            WorkflowAgent(
                "security-audit", SecurityAuditWorkflow, files=["src/"]
            ),
        ],
        gates=[
            GateSpec("Code Quality", "code-review", 80.0),
            GateSpec("Security", "security-audit", 80.0),
        ],
    )

    report = await team.run(["src/"])
    print(f"Passed: {report.passed}")
    print(f"Blockers: {report.blockers}")
    print(f"Cost: {report.cost}")

    # Record the outcome for future reuse
    store = ConfigurationStore()
    config = AgentConfiguration(
        id="comprehensive_review",
        task_pattern="release_prep",
        agents=[{"role": "code-review"}, {"role": "security-audit"}],
        strategy="parallel",
        quality_gates={"min_score": 80.0},
    )
    quality_score = 85.0 if report.passed else 50.0
    config.record_outcome(report.passed, quality_score)
    store.save(config)

asyncio.run(main())
```

---

## Type Hints

**All public APIs have complete type hints:**

```python
from typing import Any, Dict, List

from attune.orchestration import AgentTemplate
from attune.orchestration.execution_strategies import StrategyResult
from attune.orchestration.config_store import AgentConfiguration

# Aliases for backward compatibility
Context = Dict[str, Any]
AgentList = List[AgentTemplate]
QualityGates = Dict[str, Any]

# Return types
def make_result() -> StrategyResult: ...
def search() -> list[AgentConfiguration]: ...
```

---

## Error Handling

**All functions validate inputs and raise appropriate exceptions:**

```python
import asyncio

from attune.orchestration import get_template
from attune.orchestration.execution_strategies import get_strategy

template = get_template("invalid_id")
if template is None:
    print("Template not found")

try:
    strategy = get_strategy("not_a_strategy")
except ValueError as e:
    print(f"Invalid strategy: {e}")

try:
    strategy = get_strategy("parallel")
    asyncio.run(strategy.execute([], {}))
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
