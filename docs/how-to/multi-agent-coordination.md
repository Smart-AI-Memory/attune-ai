---
description: "Multi-Agent Coordination: run specialized Attune workflows together, sharing discovered patterns through a common PatternLibrary."
---

# Multi-Agent Coordination

Run multiple specialized Attune workflows together on complex tasks,
sharing discovered patterns through a common `PatternLibrary` and
tracking activity with `AgentMonitor`.

---

## Overview

Specialized workflows can collaborate on a change set:

- **Code Review** - reviews diffs for bugs and style
- **Test Generation** - creates unit and integration tests
- **Documentation** - maintains up-to-date docs
- **Security Audit** - scans for vulnerabilities
- **Performance Audit** - finds slow code

Running them in parallel and sharing learnings through one pattern
library means each workflow benefits from what the others discover.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                    Shared Pattern Library                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ • Code patterns discovered by any workflow             │  │
│  │ • Best practices learned from the team                 │  │
│  │ • Security vulnerabilities and fixes                   │  │
│  │ • Performance optimizations                            │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬────────────────────────────────────────┘
                       │ (Shared Knowledge)
        ┌──────────────┼───────────────┬────────────┐
        │              │               │            │
        ▼              ▼               ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────┐
│ Code Review  │ │   Test   │ │ Documentation │ │  Security  │
│   Workflow   │ │Generation│ │   Workflow    │ │   Audit    │
└──────┬───────┘ └────┬─────┘ └──────┬───────┘ └─────┬──────┘
       │              │                │              │
       │ (Results)    │                │              │
       └──────────────┴────────────────┴──────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │  Coordinated Output  │
            └──────────────────────┘
```

---

## Quick Start

### Create a Shared Pattern Library

```python
from attune import PatternLibrary

# One shared pattern library for every workflow on the team
shared_library = PatternLibrary()

# Inspect what the library holds
stats = shared_library.get_library_stats()
print(stats)
```

### Run a Coordinated Workflow

```python
import asyncio

from attune.workflows import (
    CodeReviewWorkflow,
    ParallelTestGenerationWorkflow,
    DocumentGenerationWorkflow,
)


async def process_pull_request(pr_number: int):
    # 1. Code review (parallel)
    review_task = CodeReviewWorkflow().execute(pr=pr_number)

    # 2. Generate tests (parallel)
    test_task = ParallelTestGenerationWorkflow().execute()

    # 3. Update docs (parallel)
    doc_task = DocumentGenerationWorkflow().execute(pr=pr_number)

    # Wait for all workflows to complete
    review, tests, docs = await asyncio.gather(
        review_task,
        test_task,
        doc_task,
    )

    return {
        "review": review,
        "tests": tests,
        "documentation": docs,
    }
```

---

## Pattern Sharing

### How It Works

1. A workflow discovers a useful pattern.
2. The pattern is contributed to the **shared library** with a
   confidence score.
3. Another workflow encounters a similar context.
4. The pattern is suggested if its confidence clears the threshold.
5. Success/failure feedback updates the pattern's confidence.

### Example: Code Pattern

```python
from attune import PatternLibrary, Pattern

shared_library = PatternLibrary()

# Code review discovers a pattern
pattern = Pattern(
    id="avoid_mutable_defaults",
    agent_id="code_reviewer",
    pattern_type="warning",
    name="Avoid mutable default arguments",
    description="Mutable default arguments are shared across calls.",
    context={
        "language": "python",
        "issue": "mutable_default_argument",
    },
    code=(
        "# Bad (mutable default)\n"
        "def append_to_list(item, my_list=[]):\n"
        "    my_list.append(item)\n"
        "    return my_list\n"
        "\n"
        "# Good (immutable default)\n"
        "def append_to_list(item, my_list=None):\n"
        "    if my_list is None:\n"
        "        my_list = []\n"
        "    my_list.append(item)\n"
        "    return my_list\n"
    ),
    confidence=0.95,
    tags=["python", "defaults"],
)

# Contribute it to the shared library
shared_library.contribute_pattern("code_reviewer", pattern)

# Later, another workflow queries for similar context
matches = shared_library.query_patterns(
    agent_id="test_generator",
    context={"language": "python", "function_has_default": True},
)

for match in matches:
    print(f"Suggested pattern: {match.pattern.name}")

# Record whether applying the pattern worked
shared_library.record_pattern_outcome("avoid_mutable_defaults", success=True)
```

---

## Coordination Patterns

### Sequential Workflow

Workflows run in sequence, each gating the next:

```python
from attune.workflows import (
    SecurityAuditWorkflow,
    ParallelTestGenerationWorkflow,
    CodeReviewWorkflow,
)


async def sequential_workflow():
    # 1. Security scan first
    security = await SecurityAuditWorkflow().execute()

    # 2. Generate tests
    tests = await ParallelTestGenerationWorkflow().execute()

    # 3. Review code and tests
    review = await CodeReviewWorkflow().execute()

    return {
        "security": security,
        "tests": tests,
        "review": review,
    }
```

### Parallel Workflow

Workflows run simultaneously for speed:

```python
import asyncio

from attune.workflows import (
    SecurityAuditWorkflow,
    ParallelTestGenerationWorkflow,
    CodeReviewWorkflow,
    DocumentGenerationWorkflow,
)


async def parallel_workflow():
    security, tests, review, docs = await asyncio.gather(
        SecurityAuditWorkflow().execute(),
        ParallelTestGenerationWorkflow().execute(),
        CodeReviewWorkflow().execute(),
        DocumentGenerationWorkflow().execute(),
    )

    return {
        "security": security,
        "tests": tests,
        "review": review,
        "documentation": docs,
    }
```

---

## Monitoring

### Agent Performance

`AgentMonitor` shares the same pattern library so monitoring and
pattern sharing stay in sync.

```python
from attune import PatternLibrary
from attune.monitoring import AgentMonitor

monitor = AgentMonitor(pattern_library=PatternLibrary())

# Record activity as workflows run
monitor.record_interaction("code_reviewer", response_time_ms=120.0)
monitor.record_pattern_discovery("code_reviewer", pattern_id="p1")

# Read per-agent metrics
stats = monitor.get_agent_stats("code_reviewer")
print(f"Interactions: {stats['total_interactions']}")
print(f"Avg response time: {stats['avg_response_time_ms']}ms")
print(f"Patterns discovered: {stats['patterns_discovered']}")
print(f"Success rate: {stats['success_rate']:.0%}")
```

### Team Metrics

```python
from attune.monitoring import AgentMonitor

monitor = AgentMonitor()

team_stats = monitor.get_team_stats()

print(f"Active agents: {team_stats['active_agents']}")
print(f"Shared patterns: {team_stats['shared_patterns']}")
print(f"Pattern reuse rate: {team_stats['pattern_reuse_rate']:.0%}")
print(f"Collaboration efficiency: {team_stats['collaboration_efficiency']:.0%}")
```

---

## Best Practices

### Do

1. **Specialize workflows** - each focuses on one area.
2. **Share patterns** - use a single shared pattern library.
3. **Run in parallel** when possible to maximize speed.
4. **Monitor performance** - track workflow effectiveness.
5. **Record outcomes** - feed success/failure back into patterns.

### Don't

1. **Don't duplicate work** - query the pattern library first.
2. **Don't ignore low-confidence patterns** - provide feedback.
3. **Don't create too many workflows at once** - start with 3-5.
4. **Don't skip coordination** - workflows need orchestration.

---

## See Also

- [Pattern Library API](../reference/pattern-library.md) - pattern
  management
- [Multi-Agent Example](../tutorials/examples/multi-agent-team-coordination.md)
  - full implementation
