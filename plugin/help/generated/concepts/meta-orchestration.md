---
name: meta-orchestration
source: src/attune/orchestration/
summary: This template covers six meta-orchestration patterns—Sequential, Parallel,
  Debate, Teaching, Refinement, and Adaptive—that define how to compose multiple workflows
  into coordinated pipelines by controlling execution order, data flow, and quality
  gates.
tags:
- architecture
- workflow
type: concept
---

# Meta-orchestration patterns

Meta-orchestration patterns are composition strategies for combining multiple workflows into coordinated pipelines. The orchestration module provides six patterns, each defining how workflows execute, how data flows between stages, and where quality gates apply.

## Why meta-orchestration matters

Complex tasks rarely map to a single workflow. A release preparation pipeline, for example, requires a security audit, a dependency check, and a documentation review — each feeding results into the next. Meta-orchestration handles the sequencing, data handoff, and failure logic so individual workflows stay focused on their own responsibilities.

## Available patterns

| Pattern | Description |
|---|---|
| **Sequential** | Workflows run one after another. Each stage receives the output of the previous stage. |
| **Parallel** | Workflows run simultaneously. Results are collected and merged when all stages complete. |
| **Debate** | Two or more workflows analyze the same input independently, then reconcile their conclusions. |
| **Teaching** | A primary workflow produces output that a secondary workflow critiques or annotates. |
| **Refinement** | A workflow runs repeatedly, using its own previous output as input, until a quality threshold is met. |
| **Adaptive** | The orchestrator selects which workflow to run next based on the results of the current stage. |

## How it works

The orchestration module composes `BaseWorkflow` instances using the selected pattern. Each pattern controls three things:

- **Execution order** — when each workflow runs relative to others
- **Data flow** — how outputs from one stage become inputs to the next
- **Quality gates** — conditions that must be satisfied before the pipeline advances or completes

## Example: Secure Release pipeline

The Secure Release pipeline uses the **Sequential** pattern across three stages:

```
security_audit → dependency_check → release_prep
```

Each stage must pass its quality gate before the next stage begins. If `security_audit` surfaces critical findings, the pipeline halts before `release_prep` runs.

## Related topics

*No related topics yet.*
