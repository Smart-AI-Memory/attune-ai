---
description: Meta-Orchestration API API reference: **Version:** 4.0.0 (New in v4.0) **Module:** `attune.orchestration` **Stability:** 🟢 Stable (Pub
---

# Meta-Orchestration API

**Version:** 4.0.0 (New in v4.0)
**Module:** `attune.orchestration`
**Stability:** 🟢 Stable (Public API)

---

## Overview

The Meta-Orchestration API enables automatic task analysis, agent selection, and composition pattern selection. Instead of manually wiring agent workflows, the system analyzes your task and composes the optimal team automatically.

**Key Features:**
- 🧠 Automatic task complexity analysis
- 🤝 Dynamic agent team selection (7 pre-built templates)
- 📐 Intelligent strategy selection (6 composition patterns)
- 📚 Learning system saves successful compositions
- ⚡ Production-ready workflows (release prep, test coverage boost)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [MetaOrchestrator Class](#metaorchestrator-class)
3. [Data Structures](#data-structures)
4. [Agent Templates](#agent-templates)
5. [Composition Patterns](#composition-patterns)
6. [Configuration Store](#configuration-store)
7. [Built-In Orchestrated Workflows](#built-in-orchestrated-workflows)
8. [Examples](#examples)
9. [Advanced Usage](#advanced-usage)

---

## Quick Start

### Basic Usage

```python
from attune.orchestration import MetaOrchestrator

# Create orchestrator
orchestrator = MetaOrchestrator()

# Analyze task and get execution plan
plan = orchestrator.analyze_and_compose(
    task="Boost test coverage to 90%",
    context={"current_coverage": 75}
)

# Inspect the plan
print(f"Strategy: {plan.strategy}")
# → sequential

print(f"Agents: {[a.role for a in plan.agents]}")
# → ['Test Coverage Expert', 'Test Generation Specialist', 'Quality Assurance Validator']

print(f"Estimated cost: ${plan.estimated_cost:.2f}")
# → $2.15

print(f"Estimated duration: {plan.estimated_duration}s")
# → 180
```

### Using Built-In Orchestrated Workflows

```python
from attune.workflows.orchestrated_release_prep import (
    OrchestratedReleasePrepWorkflow
)

# Release preparation with 4 parallel agents
workflow = OrchestratedReleasePrepWorkflow(
    quality_gates={
        "min_coverage": 90.0,
        "max_critical_issues": 0,
    }
)

report = await workflow.execute(path=".")

if report.approved:
    print(f"✅ Release approved! (confidence: {report.confidence})")
else:
    for blocker in report.blockers:
        print(f"❌ {blocker}")
```

---

## MetaOrchestrator Class

### `attune.orchestration.MetaOrchestrator`

The core orchestration engine that analyzes tasks and composes agent teams.

#### Constructor

```python
orchestrator = MetaOrchestrator()
```

**Parameters:** None

**Returns:** `MetaOrchestrator` instance

---

#### `analyze_and_compose()`

Main entry point for meta-orchestration. Analyzes task and creates execution plan.

```python
plan = orchestrator.analyze_and_compose(
    task: str,
    context: dict[str, Any] | None = None
) -> ExecutionPlan
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task` | `str` | Yes | - | Task description (e.g., "Improve test coverage") |
| `context` | `dict[str, Any]` | No | `{}` | Additional context (current state, constraints, etc.) |

**Returns:** `ExecutionPlan` with selected agents and composition strategy

**Raises:**
- `ValueError` - If task is empty or invalid

**Example:**

```python
orchestrator = MetaOrchestrator()

# Simple task
plan = orchestrator.analyze_and_compose("Run security audit")

# With context
plan = orchestrator.analyze_and_compose(
    task="Boost test coverage",
    context={
        "current_coverage": 75,
        "target_coverage": 90,
        "priority": "high"
    }
)
```

**Execution Steps:**
1. `_analyze_task()` - Extracts requirements (complexity, domain, capabilities)
2. `_select_agents()` - Chooses agents matching requirements
3. `_choose_composition_pattern()` - Selects optimal strategy
4. Creates `ExecutionPlan` with cost/duration estimates

---

### Private Methods

**⚠️ Note:** These methods are private (`_method`) but documented here for understanding. **Do not call directly** - use `analyze_and_compose()` instead.

#### `_analyze_task()`

🔴 **Private API** - Do not call directly

Analyzes task description to extract requirements.

```python
requirements = orchestrator._analyze_task(task, context)
# Returns: TaskRequirements
```

**Workaround:** Call `analyze_and_compose()` which includes this step.

**Future:** May become public in v4.1 (see [ARCHITECTURAL_GAPS_ANALYSIS.md](../ARCHITECTURAL_GAPS_ANALYSIS.md#gap-11))

---

#### `_select_agents()`

🔴 **Private API** - Do not call directly

Selects agents based on task requirements.

```python
agents = orchestrator._select_agents(requirements)
# Returns: list[AgentTemplate]
```

**Workaround:** Call `analyze_and_compose()` which includes this step.

---

#### `_choose_composition_pattern()`

🔴 **Private API** - Do not call directly

Chooses optimal composition pattern.

```python
strategy = orchestrator._choose_composition_pattern(requirements, agents)
# Returns: CompositionPattern
```

**Workaround:** Call `analyze_and_compose()` which includes this step.

---

## Data Structures

### `ExecutionPlan`

Result of task analysis containing agents and execution strategy.

```python
@dataclass
class ExecutionPlan:
    agents: list[AgentTemplate]
    strategy: CompositionPattern
    quality_gates: dict[str, Any]
    estimated_cost: float
    estimated_duration: int  # seconds
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `agents` | `list[AgentTemplate]` | Selected agents for execution |
| `strategy` | `CompositionPattern` | Composition pattern (Sequential, Parallel, etc.) |
| `quality_gates` | `dict[str, Any]` | Quality thresholds to enforce |
| `estimated_cost` | `float` | Estimated cost in USD |
| `estimated_duration` | `int` | Estimated time in seconds |

**Example:**

```python
plan = orchestrator.analyze_and_compose("Security audit")

print(f"Agents: {[a.role for a in plan.agents]}")
print(f"Strategy: {plan.strategy.value}")
print(f"Cost: ${plan.estimated_cost:.2f}")
print(f"Duration: {plan.estimated_duration}s")
```

---

### `TaskRequirements`

🔴 **Private Type** - Returned by private `_analyze_task()` method

Extracted requirements from task analysis.

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

**Access:** Use `analyze_and_compose()` - this type is internal

---

### Enumerations

#### `TaskComplexity`

```python
class TaskComplexity(Enum):
    SIMPLE = "simple"      # Single agent, straightforward
    MODERATE = "moderate"  # 2-3 agents, some coordination
    COMPLEX = "complex"    # 4+ agents, multi-phase execution
```

**Keyword Matching:**
- **SIMPLE**: "format", "lint", "check", "validate", "document"
- **MODERATE**: "improve", "refactor", "optimize", "test", "review"
- **COMPLEX**: "release", "migrate", "redesign", "architecture", "prepare"

---

#### `TaskDomain`

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

**Keyword Matching:**
- **TESTING**: "test", "coverage", "pytest", "unit test"
- **SECURITY**: "security", "vulnerability", "audit", "OWASP"
- **CODE_QUALITY**: "review", "quality", "best practices", "lint"
- **DOCUMENTATION**: "docs", "documentation", "README", "API docs"
- **PERFORMANCE**: "performance", "optimize", "slow", "bottleneck"
- **ARCHITECTURE**: "architecture", "design", "patterns", "structure"
- **REFACTORING**: "refactor", "cleanup", "technical debt"

---

#### `CompositionPattern`

```python
class CompositionPattern(Enum):
    SEQUENTIAL = "sequential"  # A → B → C
    PARALLEL = "parallel"      # A || B || C
    DEBATE = "debate"          # A ⇄ B ⇄ C → Synthesis
    TEACHING = "teaching"      # Junior → Expert validation
    REFINEMENT = "refinement"  # Draft → Review → Polish
    ADAPTIVE = "adaptive"      # Classifier → Specialist
```

**When Each Pattern is Used:**

| Pattern | Use When | Example Task |
|---------|----------|--------------|
| **Sequential** | Steps depend on previous output | "Boost coverage" (analyze → generate → validate) |
| **Parallel** | Independent validations can run concurrently | "Release prep" (security + tests + docs + quality) |
| **Debate** | Need consensus from multiple perspectives | "Architecture review" (debate trade-offs) |
| **Teaching** | Most tasks simple, escalate complex ones | "Code review" (junior first, expert if needed) |
| **Refinement** | Quality > speed, iterative improvement | "Write documentation" (draft → review → polish) |
| **Adaptive** | Unknown complexity upfront | "Analyze codebase" (classify first, then route) |

---

## Agent Templates

The framework includes 7 pre-built agent templates. Templates define agent capabilities and tier requirements.

### Available Templates

```python
from attune.orchestration.agent_templates import get_template, get_all_templates

# Get specific template
security_agent = get_template("security_auditor")

# Get all templates
all_agents = get_all_templates()

# Get by capability
test_agents = get_templates_by_capability("testing")
```

### Template Details

| Template ID | Role | Capabilities | Tier |
|-------------|------|--------------|------|
| `security_auditor` | Security Auditor | vulnerability_scan, threat_modeling, compliance_check | CAPABLE |
| `test_coverage_analyzer` | Test Coverage Expert | analyze_coverage, identify_gaps, suggest_tests | CAPABLE |
| `code_quality_reviewer` | Code Quality Reviewer | code_review, quality_assessment, best_practices_check | CAPABLE |
| `documentation_writer` | Documentation Writer | generate_docs, check_completeness, update_examples | CHEAP |
| `performance_profiler` | Performance Profiler | profile_code, identify_bottlenecks, suggest_optimizations | PREMIUM |
| `dependency_checker` | Dependency Checker | scan_dependencies, check_updates, analyze_licenses | CHEAP |
| `architecture_reviewer` | Architecture Reviewer | analyze_architecture, identify_patterns, suggest_improvements | PREMIUM |

### AgentTemplate Structure

```python
@dataclass
class AgentTemplate:
    id: str
    role: str
    capabilities: list[str]
    tier: str  # "CHEAP", "CAPABLE", "PREMIUM"
    description: str
    specialization: str
```

**Example:**

```python
security_agent = get_template("security_auditor")

print(f"Role: {security_agent.role}")
# → "Security Auditor"

print(f"Capabilities: {security_agent.capabilities}")
# → ["vulnerability_scan", "threat_modeling", "compliance_check"]

print(f"Tier: {security_agent.tier}")
# → "CAPABLE"
```

---

## Composition Patterns

### 1. Sequential (Pipeline)

```
Agent A → Agent B → Agent C → Final Result
```

**Use When:**
- Each step depends on previous output
- Clear pipeline structure
- Order matters

**Example:**
```python
# Task: "Boost test coverage to 90%"
# Plan: Test Coverage Analyzer → Test Generator → Validator
plan = orchestrator.analyze_and_compose("Boost test coverage to 90%")
assert plan.strategy == CompositionPattern.SEQUENTIAL
```

---

### 2. Parallel (Validation)

```
      ┌→ Agent A →┐
Task ─┼→ Agent B →┼→ Synthesis → Final Result
      └→ Agent C →┘
```

**Use When:**
- Independent validations
- Speed is critical
- Agents don't depend on each other

**Example:**
```python
# Task: "Prepare for release"
# Plan: Security + Tests + Docs + Quality (all parallel)
plan = orchestrator.analyze_and_compose("Prepare for v4.0 release")
assert plan.strategy == CompositionPattern.PARALLEL
```

---

### 3. Debate (Consensus)

```
Agent A ⇄ Agent B ⇄ Agent C → Synthesis → Final Result
```

**Use When:**
- Need consensus
- Multiple valid perspectives
- Trade-offs to evaluate

**Example:**
```python
# Task: "Design new architecture"
# Plan: Multiple reviewers debate design choices
plan = orchestrator.analyze_and_compose("Design architecture for feature X")
# May select DEBATE pattern depending on context
```

---

### 4. Teaching (Cost Optimization)

```
Junior Agent → (if confidence < threshold) → Expert Agent
```

**Use When:**
- Most tasks are simple
- Want to optimize costs
- Expert review only when needed

**Example:**
```python
# Task: "Review this code"
# Plan: Junior reviewer first, expert if complex
plan = orchestrator.analyze_and_compose(
    task="Review code",
    context={"optimize_cost": True}
)
# May select TEACHING if cost optimization requested
```

---

### 5. Refinement (Iterative)

```
Draft Agent → Review Agent → Polish Agent → Final Result
```

**Use When:**
- Quality > speed
- Content generation
- Iterative improvement beneficial

**Example:**
```python
# Task: "Write comprehensive documentation"
# Plan: Draft → Review → Polish
plan = orchestrator.analyze_and_compose("Write API documentation")
# May select REFINEMENT for documentation tasks
```

---

### 6. Adaptive (Right-Sizing)

```
Classifier → Route to appropriate specialist
```

**Use When:**
- Unknown complexity upfront
- Need optimal resource allocation
- Task variety is high

**Example:**
```python
# Task: "Analyze codebase"
# Plan: Classifier determines what type of analysis needed
plan = orchestrator.analyze_and_compose("Analyze this codebase")
# May select ADAPTIVE when task is vague
```

---

## Configuration Store

The configuration store saves successful compositions and improves over time.

### `ConfigurationStore`

⚠️ **Note:** Full API documentation pending. Basic usage:

```python
from attune.orchestration.config_store import ConfigurationStore

store = ConfigurationStore()

# Find best composition for task
best = store.get_best_for_task("release_prep")
if best:
    print(f"Success rate: {best.success_rate:.1%}")
    print(f"Agents: {[a['role'] for a in best.agents]}")
```

**Planned Features:**
- Save successful compositions
- Track success rates
- Query by task type
- Export/import configurations

---

## Built-In Orchestrated Workflows

### Release Preparation Workflow

Parallel validation with 4 agents:

```python
from attune.workflows.orchestrated_release_prep import (
    OrchestratedReleasePrepWorkflow
)

workflow = OrchestratedReleasePrepWorkflow(
    quality_gates={
        "min_coverage": 90.0,
        "max_critical_issues": 0,
        "max_medium_issues": 5,
    }
)

report = await workflow.execute(path=".")

# Check approval
if report.approved:
    print(f"✅ Approved (confidence: {report.confidence})")
else:
    print("❌ Blocked:")
    for blocker in report.blockers:
        print(f"  - {blocker}")
```

**Agents:**
1. Security Auditor - Vulnerability scanning
2. Test Coverage Analyzer - Coverage gap analysis
3. Code Quality Reviewer - Best practices
4. Documentation Writer - Completeness check

**Strategy:** PARALLEL (all run concurrently)

---

### Test Coverage Boost Workflow

Sequential improvement workflow:

```python
from attune.workflows.orchestrated_test_coverage import (
    OrchestratedTestCoverageWorkflow
)

workflow = OrchestratedTestCoverageWorkflow(
    target_coverage=90.0
)

report = await workflow.execute(path="./src")

print(f"Coverage improved: {report.initial_coverage}% → {report.final_coverage}%")
print(f"Tests added: {report.tests_added}")
```

**Agents:**
1. Test Coverage Analyzer - Identify gaps
2. Test Generator - Create tests
3. Validator - Verify coverage

**Strategy:** SEQUENTIAL (pipeline)

---

## Examples

### Example 1: Automatic Task Analysis

```python
from attune.orchestration import MetaOrchestrator

orchestrator = MetaOrchestrator()

# Analyze different tasks
tasks = [
    "Format code with black",
    "Review code for security issues",
    "Prepare for v4.0 release",
]

for task in tasks:
    plan = orchestrator.analyze_and_compose(task)
    print(f"\nTask: {task}")
    print(f"Complexity: {plan.complexity}")  # Note: This is in TaskRequirements (private)
    print(f"Agents: {len(plan.agents)}")
    print(f"Strategy: {plan.strategy.value}")
```

**Expected Output:**

```
Task: Format code with black
Complexity: SIMPLE
Agents: 1
Strategy: sequential

Task: Review code for security issues
Complexity: MODERATE
Agents: 2
Strategy: sequential

Task: Prepare for v4.0 release
Complexity: COMPLEX
Agents: 4
Strategy: parallel
```

---

### Example 2: Custom Context

```python
plan = orchestrator.analyze_and_compose(
    task="Improve performance",
    context={
        "current_response_time": 500,  # ms
        "target_response_time": 100,   # ms
        "budget": 50.0,  # USD
        "priority": "high",
        "constraints": ["no database changes"],
    }
)

print(f"Selected agents: {[a.role for a in plan.agents]}")
print(f"Estimated cost: ${plan.estimated_cost:.2f}")

# Check if within budget
if plan.estimated_cost > context["budget"]:
    print("⚠️  Estimated cost exceeds budget!")
```

---

### Example 3: Quality Gates

```python
plan = orchestrator.analyze_and_compose(
    task="Security audit",
    context={
        "quality_gates": {
            "max_critical": 0,
            "max_high": 3,
            "max_medium": 10,
        }
    }
)

# Quality gates are preserved in plan
print(f"Quality gates: {plan.quality_gates}")
# → {'max_critical': 0, 'max_high': 3, 'max_medium': 10}
```

---

## Advanced Usage

### Cost Estimation

```python
plan = orchestrator.analyze_and_compose("Comprehensive security audit")

print(f"Estimated cost breakdown:")
for agent in plan.agents:
    tier_cost = {
        "CHEAP": 0.008,
        "CAPABLE": 0.090,
        "PREMIUM": 0.450,
    }
    agent_cost = tier_cost[agent.tier]
    print(f"  {agent.role} ({agent.tier}): ${agent_cost:.3f}")

print(f"Total: ${plan.estimated_cost:.2f}")
```

---

### Duration Estimation

```python
plan = orchestrator.analyze_and_compose("Release preparation")

print(f"Estimated duration: {plan.estimated_duration}s")

if plan.strategy == CompositionPattern.PARALLEL:
    print("Agents run in parallel - duration is max of individual times")
elif plan.strategy == CompositionPattern.SEQUENTIAL:
    print("Agents run sequentially - duration is sum of individual times")
```

---

### Inspecting Agent Selection

```python
plan = orchestrator.analyze_and_compose("Security and performance audit")

print("Selected agents:")
for agent in plan.agents:
    print(f"\n{agent.role}:")
    print(f"  Capabilities: {', '.join(agent.capabilities)}")
    print(f"  Tier: {agent.tier}")
    print(f"  Specialization: {agent.specialization}")
```

---

## API Limitations & Future Work

### Current Limitations

1. **Private Methods** - Task analysis, agent selection, and strategy selection are private. Must use `analyze_and_compose()` for the full flow.
   - **Future:** May expose public methods in v4.1 (see [architectural gaps](../ARCHITECTURAL_GAPS_ANALYSIS.md))

2. **No Standalone Plan Creation** - Cannot create execution plans from `TaskRequirements` separately
   - **Future:** Planned `create_execution_plan(requirements)` method

3. **Limited Configuration Store** - API incomplete for saving/loading compositions
   - **Future:** Full CRUD operations planned

### Architectural Notes

See [ARCHITECTURAL_GAPS_ANALYSIS.md](../ARCHITECTURAL_GAPS_ANALYSIS.md) for complete details on:
- Gap 1.1: Private `_analyze_task()` (P2 priority)
- Gap 1.2: Method naming inconsistency (P3 priority)
- Gap 1.3: No standalone `create_execution_plan()` (P1 priority)

---

## See Also

- [Agent Templates Reference](./agent-templates.md) - All 7 pre-built templates
- [Orchestrated Workflows](./workflows.md#orchestrated-workflows) - Built-in orchestrated workflows
- [Workflow API](./workflows.md) - Creating custom workflows
- [Architecture Overview](../ARCHITECTURE.md#meta-orchestration-system-v40) - System design

---

## Feedback

Questions or issues with the Meta-Orchestration API?

- **Issues:** https://github.com/Smart-AI-Memory/attune-ai/issues
- **Discussions:** https://github.com/Smart-AI-Memory/attune-ai/discussions

---

**Last Updated:** January 16, 2026
**Maintained By:** Documentation Team
**License:** Apache License 2.0
