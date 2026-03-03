---
description: Workflows API API reference. Cost-optimized AI workflows with 3-tier model routing, parameters, examples, and usage patterns.
---

# Workflows API

Cost-optimized workflow patterns that leverage 3-tier model routing.

---

## Overview

Workflows are reusable AI automation patterns that intelligently route tasks to different model tiers based on complexity:

| Tier | Models | Use Cases |
|------|--------|-----------|
| **Cheap** | Claude Haiku | Summarization, classification, triage |
| **Capable** | Claude Sonnet | Analysis, code generation, security review |
| **Premium** | Claude Opus | Synthesis, architectural decisions, coordination |

---

## Quick Start

```python
from attune.workflows import SecurityAuditWorkflow
import asyncio

async def audit_code():
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(target_path="./src")

    print(f"Found {len(result.findings)} issues")
    print(f"Cost: ${result.cost_report.total_cost:.4f}")
    print(f"Saved: {result.cost_report.savings_percent:.1f}% vs premium-only")

asyncio.run(audit_code())
```

---

## Built-in Workflows

### Security & Quality

| Workflow | Description |
|----------|-------------|
| `SecurityAuditWorkflow` | Audit code for vulnerabilities |
| `CodeReviewWorkflow` | Comprehensive code review |
| `BugPredictionWorkflow` | Predict bugs using patterns |
| `PerformanceAuditWorkflow` | Performance analysis |

### Testing

| Workflow | Description |
|----------|-------------|
| `TestGenerationWorkflow` | Generate tests for coverage gaps |
| `TestCoverageBoostCrew` | Multi-agent test coverage boost |
| `Test5Workflow` | Level 5 testing workflow |

### Documentation & Release

| Workflow | Description |
|----------|-------------|
| `DocumentGenerationWorkflow` | Generate documentation |
| `DocumentManagerWorkflow` | Manage documentation files |
| `ReleasePreparationWorkflow` | Prepare releases |
| `SecureReleasePipeline` | Security-focused release |

### Research & Analysis

| Workflow | Description |
|----------|-------------|
| `ResearchSynthesisWorkflow` | Synthesize research documents |
| `RefactorPlanWorkflow` | Plan refactoring efforts |
| `DependencyCheckWorkflow` | Check dependencies |

---

## BaseWorkflow

Base class for all workflows.

```python
from attune.workflows import BaseWorkflow, WorkflowResult

class MyWorkflow(BaseWorkflow):
    """Custom workflow implementation."""

    async def execute(self, **kwargs) -> WorkflowResult:
        # Use tier routing
        summary = await self.call_cheap("Summarize: " + kwargs["text"])
        analysis = await self.call_capable("Analyze: " + summary)
        decision = await self.call_premium("Decide: " + analysis)

        return WorkflowResult(
            output=decision,
            cost_report=self.get_cost_report()
        )
```

### Methods

| Method | Description |
|--------|-------------|
| `call_cheap(prompt)` | Route to cheap tier (Haiku) |
| `call_capable(prompt)` | Route to capable tier (Sonnet) |
| `call_premium(prompt)` | Route to premium tier (Opus) |
| `get_cost_report()` | Get cost breakdown |

---

## WorkflowResult

Result container returned by workflows.

```python
@dataclass
class WorkflowResult:
    output: Any                    # Workflow output
    cost_report: CostReport       # Cost breakdown
    metadata: dict = field(...)   # Additional metadata
```

### CostReport

```python
@dataclass
class CostReport:
    total_cost: float             # Actual cost
    baseline_cost: float          # Premium-only cost
    savings_percent: float        # Savings percentage
    calls_by_tier: dict[str, int] # Calls per tier
```

---

## WorkflowBuilder

Fluent API for building workflows programmatically.

```python
from attune.workflows import WorkflowBuilder

workflow = (
    WorkflowBuilder()
    .add_step("triage", tier="cheap", prompt="Classify: {input}")
    .add_step("analyze", tier="capable", prompt="Analyze: {triage}")
    .add_step("decide", tier="premium", prompt="Decide: {analyze}")
    .build()
)

result = await workflow.execute(input="user request")
```

---

## Routing Strategies

Control how tasks are routed to model tiers.

```python
from attune.workflows import (
    CostOptimizedRouting,
    PerformanceOptimizedRouting,
    BalancedRouting,
)

# Cost-first (default)
workflow = SecurityAuditWorkflow(routing=CostOptimizedRouting())

# Performance-first
workflow = SecurityAuditWorkflow(routing=PerformanceOptimizedRouting())

# Balanced
workflow = SecurityAuditWorkflow(routing=BalancedRouting())
```

---

## Workflow Discovery

Workflows can be discovered via entry points.

### Registering Workflows

In your `pyproject.toml`:

```toml
[project.entry-points."empathy.workflows"]
my-workflow = "my_package.workflows:MyWorkflow"
```

### Discovering Workflows

```python
from attune.workflows import discover_workflows

workflows = discover_workflows()
for name, workflow_cls in workflows.items():
    print(f"{name}: {workflow_cls.__doc__}")
```

---

## Configuration

### WorkflowConfig

```python
from attune.workflows import WorkflowConfig, ModelConfig

config = WorkflowConfig(
    models={
        "cheap": ModelConfig(provider="anthropic", model="claude-3-haiku-20240307"),
        "capable": ModelConfig(provider="anthropic", model="claude-sonnet-4-20250514"),
        "premium": ModelConfig(provider="anthropic", model="claude-opus-4-20250514"),
    },
    max_retries=3,
    timeout_seconds=120,
)
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for Claude models |
| `ATTUNE_DEFAULT_TIER` | Default tier (cheap/capable/premium) |
| `ATTUNE_COST_OPTIMIZATION` | Enable cost optimization (true/false) |

---

## CLI Integration

Run workflows from the command line:

```bash
# List available workflows
attune workflow list

# Run a workflow
attune workflow run security-audit --path ./src

# JSON output for CI/CD
attune workflow run bug-predict --path ./src --json
```

---

## Progress Tracking

Workflows provide real-time progress feedback during execution, optimized for IDE environments like VSCode.

### Automatic Progress Output

Progress is shown automatically when running workflows. No configuration needed.

```python
from attune.workflows import SecurityAuditWorkflow
import asyncio

async def run_with_progress():
    workflow = SecurityAuditWorkflow()
    result = await workflow.execute(target_path="./src")

asyncio.run(run_with_progress())
```

**Output (in VSCode Output panel or integrated terminal):**

```text
[  0%] ► Starting security-audit... ($0.0000)
[ 33%] ► Running analyze... [CHEAP] ($0.0012) [2.3s]
[ 67%] ✓ Completed analyze ($0.0023) [4.1s]
[100%] ✓ Workflow security-audit completed ($0.0089) [12.3s]

──────────────────────────────────────────────────
Stage Summary:
  analyze: 4.1s | $0.0023
  review: 5.8s | $0.0045
  summarize: 2.4s | $0.0021
──────────────────────────────────────────────────
```

**Progress includes:**

- Percentage complete
- Current stage and tier
- Running cost
- Elapsed time
- Final stage summary with per-stage breakdown

### Custom Progress Callbacks

Subscribe to progress events programmatically.

```python
from attune.workflows.progress import ProgressUpdate

def my_callback(update: ProgressUpdate):
    print(f"Stage: {update.current_stage}")
    print(f"Progress: {update.percent_complete}%")
    print(f"Cost: ${update.cost_so_far:.4f}")

workflow = SecurityAuditWorkflow(progress_callback=my_callback)
```

---

## Output Formatting

Unified output components for consistent workflow results.

### WorkflowReport

Container for structured workflow output.

```python
from attune.workflows.output import WorkflowReport, Finding

report = WorkflowReport(
    title="Security Audit Report",
    summary="Found 5 issues in 23 files",
    score=85,
    level="success",  # success, warning, error
)

# Add findings section
report.add_section("Findings", [
    Finding(severity="high", file="auth.py", line=42, message="SQL injection risk"),
    Finding(severity="medium", file="api.py", line=15, message="Missing input validation"),
])

# Add recommendations
report.add_section("Recommendations", "Review all database queries for proper escaping.")
```

### Rendering Reports

Reports support both Rich (terminal) and plain text output.

```python
from attune.workflows.output import get_console

console = get_console()

if console:
    # Rich output with colors and formatting
    report.render(console, use_rich=True)
else:
    # Plain text fallback
    print(report.render(use_rich=False))
```

### MetricsPanel

Color-coded score display.

```python
from attune.workflows.output import MetricsPanel

# Render score as Rich Panel
panel = MetricsPanel.render_score(score=85, label="Security Score")
console.print(panel)

# Or plain text
text = MetricsPanel.render_plain(score=85, label="Security Score")
print(text)  # "Security Score: [OK] 85/100 (EXCELLENT)"
```

**Score levels:**

- 85-100: Excellent (green)
- 70-84: Good (yellow)
- 50-69: Needs Work (orange)
- 0-49: Critical (red)

### FindingsTable

Render findings as tables.

```python
from attune.workflows.output import Finding, FindingsTable

findings = [
    Finding(severity="high", file="auth.py", line=42, message="SQL injection"),
    Finding(severity="low", file="utils.py", message="Unused import"),
]

table = FindingsTable(findings)

# Rich table
console.print(table.to_rich_table())

# Plain text
print(table.to_plain())
```

---

## See Also

- [Getting Started](../getting-started/choose-your-path.md#path-3-workflow-developer)
- [CLI Reference](../reference/cli-reference.md)
- [Meta-Orchestration](multi-agent.md)
