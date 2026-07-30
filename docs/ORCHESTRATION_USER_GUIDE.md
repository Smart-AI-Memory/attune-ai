---
description: Orchestration User Guide: Step-by-step tutorial with examples, best practices, and common patterns. Learn by doing with hands-on examples.
---

# Orchestration User Guide

**Version:** 11.0.0
**Last Updated:** July 29, 2026
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [CLI Reference](#cli-reference)
4. [Python API](#python-api)
5. [Agent Templates](#agent-templates)
6. [Execution Strategies](#execution-strategies)
7. [Configuration Store](#configuration-store)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Orchestration?

**Orchestration is running multiple AI agents together against a
shared target.** Attune ships ready-made orchestration-backed
workflows (release prep, test generation, …) and the lower-level
building blocks they are made from:

- **Agent templates** — reusable agent archetypes with capabilities,
  tools, and quality gates.
- **Execution strategies** — the patterns that define how agents run
  together (sequential, parallel, debate, …).
- **Agent teams** — fan-out a set of workflow-backed agents over a
  target, then gate the results against thresholds.
- **Configuration store** — a learning/memory layer that records which
  compositions worked.

The fastest way in is to run a registered workflow:

```python
# Resolve and run a registered workflow
from attune.workflows import get_workflow

workflow = get_workflow("release-prep")()
result = await workflow.execute({"path": "."})  # Done!
```

### Key Benefits

- ✅ **Faster development** - Pre-built workflows eliminate boilerplate
- ✅ **Better outcomes** - Proven compositions backed by quality gates
- ✅ **Cost optimization** - Right-sized agent tiers (CHEAP → CAPABLE → PREMIUM)
- ✅ **Learning system** - Configurations improve over time through feedback
- ✅ **Production-ready** - Comprehensive testing, security validation, monitoring

---

## Getting Started

### Installation

Orchestration ships with Attune AI:

```bash
pip install 'attune-ai[developer]'
```

### Quick Start: Release Preparation

**Run release readiness validation:**

```bash
attune workflow run release-prep
```

This runs the `ReleasePrepTeamWorkflow`, which composes a team of
validation agents (security audit, test coverage, code quality,
documentation) and reports readiness against quality gates.

> The legacy `orchestrated-release-prep` name still resolves — it is a
> migration alias for `release-prep` (`mode="full"`).

### Quick Start: Test Generation

**Generate tests for uncovered code:**

```bash
attune workflow run test-gen
```

This runs the `TestGenerationWorkflow`. The retired
`test-coverage-boost` name is a migration alias for
`test-gen` (`target="coverage"`).

---

## CLI Reference

### `attune workflow`

Orchestration-backed workflows are run through the standard
`attune workflow` command — there is no separate `attune orchestrate`
command.

```bash
attune workflow list                 # list available workflows
attune workflow info <name>          # show details for a workflow
attune workflow run <name> [opts]    # run a workflow
```

Common options for `run`:

| Option | Description |
|--------|-------------|
| `--input '<json>'` | JSON payload passed to the workflow (e.g. `'{"path": "./src"}'`) |
| `--json` | Emit machine-readable JSON instead of formatted output |

**Examples:**

```bash
# Release readiness on the current directory
attune workflow run release-prep

# Release readiness on a specific path, JSON output for CI
attune workflow run release-prep --input '{"path": "./my-project"}' --json

# Test generation targeting coverage gaps
attune workflow run test-gen --input '{"target": "coverage"}'
```

> Quality gates, target coverage, and agent selection are workflow
> inputs rather than dedicated flags; pass them in the `--input` JSON
> payload. Run `attune workflow info <name>` for a workflow's accepted
> inputs.

---

## Python API

### Running a registered workflow

The orchestration-backed workflows (`release-prep`, `test-gen`,
`orchestrated-health-check`, …) are registered in `attune.workflows`
and are normally run via `attune workflow run <name>` (above) or the
MCP tools. To drive one programmatically, resolve it from the registry:

```python
import asyncio
from attune.workflows import get_workflow

async def main():
    WorkflowClass = get_workflow("release-prep")
    workflow = WorkflowClass()
    result = await workflow.execute({"path": "."})
    print(f"Success: {result.success}")

asyncio.run(main())
```

> `OrchestratedReleasePrepWorkflow` and `TestCoverageBoostWorkflow`
> were removed in v7.0.0. Use the registered `release-prep` and
> `test-gen` workflows instead.

### Composing workflows into a team

`AgentTeam` fans out a set of workflow-backed agents over a target,
then gates each agent's score against a threshold. Build agents with
`WorkflowAgent`, declare thresholds with `GateSpec`, and run the team
against one or more paths:

```python
import asyncio
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 80.0),
        GateSpec("Security", "security-audit", 80.0),
    ],
)

report = asyncio.run(team.run(["src/"]))
print(f"Passed: {report.passed}")
print(f"Blockers: {report.blockers}")
print(f"Cost: {report.cost}")
```

`team.run(target)` accepts a path string or a list of paths and
returns a `TeamReport(passed, gates, results, blockers, warnings,
cost)`. Each entry in `report.results` is an `AgentResult(key, score,
cost, success, details)`.

---

## Agent Templates

### Overview

Agent templates are **reusable agent archetypes** with pre-defined capabilities, tools, and quality gates.

**14 pre-built templates:**

1. **Test Coverage Analyzer** - Gap analysis and test suggestions
2. **Security Auditor** - Vulnerability scanning and compliance
3. **Code Reviewer** - Quality assessment and best practices
4. **Documentation Writer** - API docs and examples
5. **Performance Optimizer** - Profiling and optimization
6. **Architecture Analyst** - Design patterns and dependencies
7. **Refactoring Specialist** - Code smells and improvements
8. **Test Generator** - Unit/integration tests and fixtures
9. **Test Validator** - Run tests and verify coverage
10. **Report Generator** - Summaries and recommendations
11. **Documentation Analyst** - Doc gaps and freshness
12. **Information Synthesizer** - Synthesis and action plans
13. **Code Simplification Specialist** - Complexity and dead-code removal
14. **General Purpose Agent** - Flexible analyze/generate/review

### Template Structure

```python
@dataclass
class AgentTemplate:
    id: str                              # Unique identifier
    role: str                            # Human-readable role
    capabilities: list[str]              # What agent can do
    tier_preference: str                 # "CHEAP", "CAPABLE", "PREMIUM"
    tools: list[str]                     # Required tools
    default_instructions: str            # Agent prompt
    quality_gates: dict[str, Any]        # Quality thresholds
    resource_requirements: ResourceRequirements  # Limits
```

### Retrieving Templates

```python
from attune.orchestration.agent_templates import (
    get_template,
    get_all_templates,
    get_templates_by_capability,
    get_templates_by_tier,
)

# Get specific template
template = get_template("test_coverage_analyzer")
print(template.role)  # "Test Coverage Expert"

# Get all templates
all_templates = get_all_templates()
print(f"Available: {len(all_templates)} templates")

# Find by capability
security_templates = get_templates_by_capability("vulnerability_scan")

# Find by tier (cost optimization)
cheap_templates = get_templates_by_tier("CHEAP")
```

### Template Capabilities Reference

| Template | Capabilities | Tier | Use Cases |
|----------|-------------|------|-----------|
| **test_coverage_analyzer** | analyze_gaps, suggest_tests, validate_coverage | CAPABLE | Gap analysis, coverage improvement |
| **security_auditor** | vulnerability_scan, threat_modeling, compliance_check | PREMIUM | Security audits, compliance validation |
| **code_reviewer** | code_review, quality_assessment, best_practices_check | CAPABLE | Code reviews, quality checks |
| **documentation_writer** | generate_docs, check_completeness, update_examples | CHEAP | API docs, tutorials, examples |
| **performance_optimizer** | profile_code, identify_bottlenecks, suggest_optimizations | CAPABLE | Performance analysis, optimization |
| **architecture_analyst** | analyze_architecture, identify_patterns, suggest_improvements | PREMIUM | Architecture review, refactoring |
| **refactoring_specialist** | identify_code_smells, suggest_refactorings, validate_changes | CAPABLE | Refactoring, technical debt |
| **test_generator** | generate_unit_tests, generate_integration_tests, create_test_fixtures | CAPABLE | Test authoring, fixtures |
| **test_validator** | validate_tests, run_tests, verify_coverage | CHEAP | Test execution, coverage verification |
| **report_generator** | generate_reports, summarize_findings, create_recommendations | CHEAP | Summaries, recommendations |
| **documentation_analyst** | analyze_docs, find_gaps, check_freshness | CAPABLE | Doc gap/freshness analysis |
| **synthesizer** | synthesize_findings, create_action_plans, prioritize_work | CAPABLE | Cross-agent synthesis, planning |
| **code_simplifier** | complexity_analysis, simplification, dead_code_removal | CAPABLE | Complexity reduction, cleanup |
| **generic_agent** | analyze, generate, review | CAPABLE | Flexible general-purpose tasks |

---

## Execution Strategies

### Overview

**Execution strategies define HOW agents work together.** Resolve a
strategy by name with `get_strategy(...)` (or import the class
directly) and call `await strategy.execute(agents, context)`.

**10 strategy patterns (13 strategy classes in the registry):**

1. **Sequential** (A → B → C) - Pipeline processing
2. **Parallel** (A ‖ B ‖ C) - Independent validation
3. **Debate** (A ⇄ B ⇄ C → Synthesis) - Consensus building
4. **Teaching** (Junior → Expert validation) - Cost optimization
5. **Refinement** (Draft → Review → Polish) - Iterative improvement
6. **Adaptive** (Classifier → Specialist) - Right-sizing
7. **Conditional** (If-then-else routing) - Branch on a condition
8. **Tool-Enhanced** (single agent + tools) - Anthropic-inspired
9. **Prompt-Cached Sequential** (shared cached context) - Anthropic-inspired
10. **Delegation Chain** (hierarchical delegation, ≤3 levels) - Anthropic-inspired

The registry also includes `multi_conditional`, `nested`, and
`nested_sequential` variants. The five core patterns below are the
most common; see the [API reference](ORCHESTRATION_API.md#execution-strategies)
for the full strategy list.

---

### 1. Sequential Strategy

**Pattern:** A → B → C
**Use when:** Tasks must be done in order, each step depends on previous results

```python
from attune.orchestration.execution_strategies import SequentialStrategy

strategy = SequentialStrategy()

# Execute agents in order
# Agent B receives Agent A's output in context
# Agent C receives Agent A + B outputs
result = await strategy.execute(agents, context)
```

**Example:**
Coverage Analyzer → Test Generator → Test Validator

**Use when:**
- Each step depends on the previous step's output
- The task is a pipeline (generate, then validate)

---

### 2. Parallel Strategy

**Pattern:** A ‖ B ‖ C
**Use when:** Independent validations needed, time optimization important

```python
from attune.orchestration.execution_strategies import ParallelStrategy

strategy = ParallelStrategy()

# Execute all agents simultaneously
# Each receives same initial context
# Results aggregated at end
result = await strategy.execute(agents, context)
```

**Example:**
Security Audit ‖ Performance Check ‖ Code Quality ‖ Docs Check

**Use when:**
- Validations are independent of one another
- Time optimization matters (bounded by the slowest agent)

**Benefits:**
- Fastest execution (bounded by slowest agent)
- Multiple perspectives on same problem
- Independent quality checks

---

### 3. Debate Strategy

**Pattern:** A ⇄ B ⇄ C → Synthesis
**Use when:** Multiple expert opinions needed, tradeoff analysis required

```python
from attune.orchestration.execution_strategies import DebateStrategy

strategy = DebateStrategy()

# Phase 1: Agents provide independent opinions (parallel)
# Phase 2: Synthesizer aggregates and resolves conflicts
result = await strategy.execute(agents, context)

# Access synthesis
consensus = result.aggregated_output["consensus"]
```

**Example:**
Architect(scale) ‖ Architect(cost) ‖ Architect(simplicity) → Synthesizer

**Use when:**
- Multiple expert opinions are needed on the same question
- Architecture decisions require tradeoff analysis

**Output structure:**
```python
{
    "debate_participants": ["agent1", "agent2", "agent3"],
    "opinions": [...],  # Individual agent outputs
    "consensus": {
        "consensus_reached": True,
        "success_votes": 3,
        "total_votes": 3,
        "avg_confidence": 0.87
    }
}
```

---

### 4. Teaching Strategy

**Pattern:** Junior → Expert validation
**Use when:** Cost-effective generation desired, quality assurance critical

```python
from attune.orchestration.execution_strategies import TeachingStrategy

# Configure quality threshold
strategy = TeachingStrategy(quality_threshold=0.7)

# Junior attempts task (CHEAP tier)
# If confidence >= 0.7: done
# If confidence < 0.7: expert takes over (CAPABLE/PREMIUM)
result = await strategy.execute([junior, expert], context)

outcome = result.aggregated_output["outcome"]
# "junior_success" or "expert_takeover"
```

**Example:**
Junior Writer(CHEAP) → Quality Gate → (pass ? done : Expert Review(CAPABLE))

**Use when:**
- Cost-effective generation is desired
- A cheaper first attempt can often clear a quality gate

**Cost savings:**
- Junior success: ~70% cost reduction
- Expert takeover: Same cost as direct expert use
- Average savings: 40-50% (assuming 60% junior success rate)

---

### 5. Refinement Strategy

**Pattern:** Draft → Review → Polish
**Use when:** Iterative improvement needed, quality ladder desired

```python
from attune.orchestration.execution_strategies import RefinementStrategy

strategy = RefinementStrategy()

# Stage 1: Drafter creates initial version (CHEAP)
# Stage 2: Reviewer improves (CAPABLE)
# Stage 3: Polisher finalizes (PREMIUM)
result = await strategy.execute([drafter, reviewer, polisher], context)

final_output = result.aggregated_output["final_output"]
```

**Example:**
Drafter(CHEAP) → Reviewer(CAPABLE) → Polisher(PREMIUM)

**Use when:**
- Iterative improvement across multiple stages is beneficial
- A quality ladder (draft → review → polish) is desired

**Benefits:**
- Progressive quality improvement
- Each stage builds on previous
- Final output is highest quality

---

### 6. Adaptive Strategy

**Pattern:** Classifier → Specialist
**Use when:** Variable task complexity, cost optimization desired

```python
from attune.orchestration.execution_strategies import AdaptiveStrategy

strategy = AdaptiveStrategy()

# Phase 1: Classifier assesses complexity (CHEAP)
# Phase 2: Route to appropriate specialist tier
result = await strategy.execute([classifier, *specialists], context)

selected = result.aggregated_output["selected_specialist"]
```

**Example:**
Classifier(CHEAP) → route(simple|moderate|complex) → Specialist(tier)

**Use when:**
- Task complexity varies run to run
- Right-sizing the model tier to the task matters

**Routing logic:**
- High confidence (>0.8) → Simple task → CHEAP specialist
- Low confidence (<0.8) → Complex task → PREMIUM specialist

**Cost savings:**
- Simple tasks: ~70% cost reduction (CHEAP instead of PREMIUM)
- Complex tasks: Same cost (PREMIUM when needed)
- Average savings: 30-40% (assuming task distribution)

---

### Selecting a Strategy

Choose a strategy by name with `get_strategy(...)` and run it
directly:

```python
from attune.orchestration.execution_strategies import get_strategy

# Pick the strategy that fits the task
strategy = get_strategy("parallel")
result = await strategy.execute(agents, context)
```

Valid names include `sequential`, `parallel`, `debate`, `teaching`,
`refinement`, `adaptive`, `conditional`, `multi_conditional`,
`nested`, `nested_sequential`, `tool_enhanced`,
`prompt_cached_sequential`, and `delegation_chain`.

---

## Configuration Store

### Overview

The **Configuration Store** is the learning/memory system for orchestration. It:
- Saves successful agent compositions
- Tracks performance metrics over time
- Retrieves proven solutions for similar tasks
- Learns from outcomes to improve future decisions

**Think of it as:** A database of "what worked" that grows smarter over time.

### Architecture

```
.attune/orchestration/compositions/
├── release_prep_001.json
├── test_gen_001.json
└── security_deep_dive_001.json
```

Each configuration stores:
- Agent team composition
- Execution strategy used
- Quality gates enforced
- Performance metrics (success rate, quality score)
- Usage statistics

---

### Basic Usage

```python
from attune.orchestration.config_store import (
    ConfigurationStore,
    AgentConfiguration,
)

# Initialize store
store = ConfigurationStore()

# Save successful composition
config = AgentConfiguration(
    id="comp_release_001",
    task_pattern="release_preparation",
    agents=[
        {"role": "security_auditor", "tier": "PREMIUM"},
        {"role": "test_analyzer", "tier": "CAPABLE"},
    ],
    strategy="parallel",
    quality_gates={"min_coverage": 80},
)

store.save(config)

# Load for reuse
loaded = store.load("comp_release_001")

# Search for similar tasks
matches = store.search(
    task_pattern="release_preparation",
    min_success_rate=0.8,
)

for match in matches:
    print(f"{match.id}: {match.success_rate:.1%} success")
```

---

### Recording Outcomes

```python
# After execution, record outcome
config = store.load("comp_release_001")

# Record successful execution
config.record_outcome(
    success=True,
    quality_score=87.5,  # 0-100
)

# Save updated metrics
store.save(config)

# Metrics are automatically updated:
# - usage_count: 1 → 2
# - success_count: 1 → 2
# - success_rate: recalculated
# - avg_quality_score: weighted average
# - last_used: updated to now
```

---

### Searching Configurations

```python
# Find best for specific task
best = store.get_best_for_task("release_preparation")
print(f"Best: {best.id} ({best.success_rate:.1%})")

# Search with filters
matches = store.search(
    task_pattern="test_coverage",
    min_success_rate=0.75,      # 75%+ success
    min_quality_score=80.0,     # Score >= 80
    limit=5,                     # Top 5 results
)

# List all configurations
all_configs = store.list_all()  # Sorted by last_used
```

---

### Integration with Workflows

**Workflows automatically use the configuration store:**

```python
from attune.workflows import get_workflow

workflow = get_workflow("release-prep")()

# On first run:
# 1. Executes with default agents
# 2. Records outcome in store
# 3. Saves successful composition

# On subsequent runs:
# 1. Checks store for proven composition
# 2. Reuses if found (faster, more reliable)
# 3. Falls back to a default composition if none found
```

**Manual integration:**

```python
from attune.orchestration.config_store import ConfigurationStore
from attune.orchestration import get_template
from attune.orchestration.execution_strategies import get_strategy

store = ConfigurationStore()

# Try to load a proven composition; fall back to a default
best = store.get_best_for_task("release_prep")

if best and best.success_rate >= 0.8:
    # Reuse the proven composition
    agents = [get_template(a["role"]) for a in best.agents]
    strategy = get_strategy(best.strategy)
else:
    # Compose a default team and strategy
    agents = [get_template("security_auditor"), get_template("code_reviewer")]
    strategy = get_strategy("parallel")

# Execute...
```

---

### Pattern Library Integration

**Successful compositions contribute to the pattern library:**

```python
from attune.pattern_library import PatternLibrary

store = ConfigurationStore(
    pattern_library=PatternLibrary()
)

# Save configuration
store.save(config)

# After 3+ successful uses with 70%+ success rate:
# → Automatically contributes pattern to library
# → Pattern becomes available for cross-task learning
```

**Benefits:**
- Patterns learned from release prep can inform security audits
- Cross-workflow knowledge sharing
- Framework-wide learning loop

---

## Advanced Usage

### Custom Workflows

**Pick templates, run a strategy, and record the outcome:**

```python
from dataclasses import dataclass
from attune.orchestration import get_template
from attune.orchestration.execution_strategies import get_strategy
from attune.orchestration.config_store import (
    ConfigurationStore,
    AgentConfiguration,
)

@dataclass
class CustomWorkflowResult:
    success: bool
    quality_score: float

class CustomWorkflow:
    """Custom workflow composed from templates and a strategy."""

    def __init__(self):
        self.config_store = ConfigurationStore()

    async def execute(self, context: dict) -> CustomWorkflowResult:
        # Step 1: Reuse a proven composition, or pick a default team
        task_pattern = "custom_workflow"
        best = self.config_store.get_best_for_task(task_pattern)

        if best and best.success_rate >= 0.8:
            agents = [get_template(a["role"]) for a in best.agents]
            strategy = get_strategy(best.strategy)
        else:
            agents = [
                get_template("security_auditor"),
                get_template("code_reviewer"),
            ]
            strategy = get_strategy("parallel")

        # Step 2: Execute
        result = await strategy.execute(agents, context)

        # Step 3: Evaluate quality
        quality_score = self._calculate_quality(result)
        success = quality_score >= 70.0

        # Step 4: Save/update configuration
        if not best:
            best = AgentConfiguration(
                id=f"comp_{task_pattern}_{self._generate_id()}",
                task_pattern=task_pattern,
                agents=[{
                    "role": a.id,
                    "tier": a.tier_preference,
                } for a in agents],
                strategy="parallel",
                quality_gates={"min_quality": 70.0},
            )

        best.record_outcome(success, quality_score)
        self.config_store.save(best)

        return CustomWorkflowResult(
            success=success,
            quality_score=quality_score,
        )

    def _calculate_quality(self, result) -> float:
        # Your quality calculation logic
        return 85.0

    def _generate_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]
```

---

### Custom Agent Templates

**Define your own agent templates:**

```python
from attune.orchestration.agent_templates import (
    AgentTemplate,
    ResourceRequirements,
)

# Create custom template
custom_template = AgentTemplate(
    id="data_pipeline_expert",
    role="Data Pipeline Specialist",
    capabilities=[
        "pipeline_design",
        "data_validation",
        "performance_tuning",
    ],
    tier_preference="CAPABLE",
    tools=["spark", "airflow", "dbt"],
    default_instructions="""
You are a data pipeline expert. Your tasks:
1. Design scalable data pipelines
2. Validate data quality and integrity
3. Optimize pipeline performance
4. Ensure fault tolerance and monitoring

Focus on production-ready, maintainable solutions.
    """.strip(),
    quality_gates={
        "min_data_quality": 99.0,
        "max_pipeline_latency": 60,  # seconds
    },
    resource_requirements=ResourceRequirements(
        min_tokens=3000,
        max_tokens=20000,
        timeout_seconds=900,
        memory_mb=2048,
    ),
)

# Register so get_template("data_pipeline_expert") resolves it
from attune.orchestration import register_custom_template

register_custom_template(custom_template)
```

---

### Multi-Stage Workflows

**Chain strategies, feeding each stage's output into the next:**

```python
from attune.orchestration import get_template
from attune.orchestration.execution_strategies import get_strategy

async def multi_stage_workflow(context: dict):
    """Complex workflow with multiple strategy stages."""

    # Stage 1: Parallel analysis
    analysis_agents = [
        get_template("security_auditor"),
        get_template("code_reviewer"),
    ]
    analysis_result = await get_strategy("parallel").execute(
        analysis_agents,
        context,
    )

    # Stage 2: Sequential fixes (based on analysis)
    fix_context = {
        **context,
        "analysis": analysis_result.aggregated_output,
    }
    fix_agents = [get_template("refactoring_specialist")]
    fix_result = await get_strategy("sequential").execute(
        fix_agents,
        fix_context,
    )

    # Stage 3: Validation (parallel)
    validation_agents = [get_template("test_validator")]
    validation_result = await get_strategy("parallel").execute(
        validation_agents,
        {**fix_context, "fixes": fix_result.aggregated_output},
    )

    return {
        "analysis": analysis_result,
        "fixes": fix_result,
        "validation": validation_result,
    }
```

---

## Troubleshooting

### Common Issues

#### 1. "Template not found"

**Problem:** `get_template(...)` was called with an unknown id.

**Solution:**
```python
# Check available templates
from attune.orchestration import get_all_templates

templates = get_all_templates()
print(f"Available: {[t.id for t in templates]}")

# Compose explicitly from chosen templates and run a strategy
from attune.orchestration import get_template
from attune.orchestration.execution_strategies import get_strategy

agents = [get_template("security_auditor"), get_template("code_reviewer")]
result = await get_strategy("parallel").execute(agents, {"path": "."})
```

#### 2. Quality gates always failing

**Problem:** Gate thresholds too strict for your project.

**Solution:**
```python
# Lower the GateSpec thresholds when building an AgentTeam
from attune.agents.team import AgentTeam, GateSpec, WorkflowAgent
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow

team = AgentTeam(
    agents=[
        WorkflowAgent("code-review", CodeReviewWorkflow, files=["src/"]),
        WorkflowAgent("security-audit", SecurityAuditWorkflow, files=["src/"]),
    ],
    gates=[
        GateSpec("Code Quality", "code-review", 60.0),  # lower from 80
        GateSpec("Security", "security-audit", 60.0),
    ],
)
```

#### 3. Execution timeout

**Problem:** Agents taking too long to execute.

**Solution:**
```python
# Increase agent timeout
from attune.orchestration.agent_templates import (
    AgentTemplate,
    ResourceRequirements,
)

custom_template = AgentTemplate(
    # ...
    resource_requirements=ResourceRequirements(
        timeout_seconds=1800,  # 30 minutes instead of 5
    )
)
```

#### 4. Configuration store not saving

**Problem:** Permissions issue or invalid path.

**Solution:**
```python
# Use custom storage directory with write permissions
store = ConfigurationStore(
    storage_dir="/tmp/orchestration_configs"
)

# Or check current directory
import os
print(f"Current dir: {os.getcwd()}")
print(f"Writable: {os.access('.attune', os.W_OK)}")
```

---

### Debugging Tips

**Enable debug logging:**

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("attune.orchestration")
logger.setLevel(logging.DEBUG)

# Now see detailed orchestration decisions
from attune.workflows import get_workflow

workflow = get_workflow("release-prep")()
result = await workflow.execute({"path": "."})
```

**Validate agent results:**

```python
result = await strategy.execute(agents, context)

for agent_result in result.outputs:
    print(f"\nAgent: {agent_result.agent_id}")
    print(f"Success: {agent_result.success}")
    print(f"Confidence: {agent_result.confidence}")
    print(f"Duration: {agent_result.duration_seconds:.2f}s")

    if not agent_result.success:
        print(f"Error: {agent_result.error}")
    else:
        print(f"Output keys: {list(agent_result.output.keys())}")
```

---

### Performance Optimization

**Reduce execution time:**

```python
# 1. Use parallel strategy when possible
strategy = get_strategy("parallel")

# 2. Use cheaper tiers for non-critical tasks
from attune.orchestration.agent_templates import get_templates_by_tier

cheap_agents = get_templates_by_tier("CHEAP")

# 3. Limit number of agents
agents = [get_template("security_auditor"),
          get_template("test_coverage_analyzer")]  # Only 2
result = await get_strategy("parallel").execute(agents, {"path": "."})

# 4. Reuse proven configurations (automatic)
store = ConfigurationStore()
best = store.get_best_for_task("release_prep")
# Uses cached composition instead of re-analyzing
```

---

### Getting Help

**Resources:**
- [API Documentation](ORCHESTRATION_API.md)
- [GitHub Issues](https://github.com/Smart-AI-Memory/attune-ai/issues)
- [GitHub Discussions](https://github.com/Smart-AI-Memory/attune-ai/discussions)
- [Example Code](../examples/orchestration/)

**Report bugs:**
```bash
attune workflow run release-prep --json > debug.json

# Then attach debug.json to your issue
```

---

## Next Steps

1. **Try the built-in workflows:**
   ```bash
   attune workflow run release-prep
   attune workflow run test-gen --input '{"target": "coverage"}'
   ```

2. **Read the API documentation:** [ORCHESTRATION_API.md](ORCHESTRATION_API.md)

3. **Explore examples:** [examples/orchestration/](../examples/orchestration/)

4. **Build custom workflows:** See [Advanced Usage](#advanced-usage)

5. **Contribute patterns:** Successful compositions automatically improve the system!

---

**Questions or feedback?** Open an issue or discussion on GitHub!
